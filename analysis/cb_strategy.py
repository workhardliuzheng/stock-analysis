"""
可转债双低策略模块

核心逻辑:
  双低值 = 转债价格 + 转股溢价率(百分比) × 1
  月频轮动，选双低最小 Top N 等权持有

数据源:
  - cb_basic: 转股价 conv_price
  - cb_daily: 转债价格 close, 成交量 vol
  - stock_daily_basic: 正股价格 close

用法:
    from analysis.cb_strategy import CbDualLowStrategy

    strategy = CbDualLowStrategy()
    recs = strategy.get_recommendations('20260430', top_n=10)
    result = strategy.backtest('20250601', '20260430', top_n=10)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from dataclasses import dataclass, field
from sqlalchemy import text

from mysql_connect.db import get_session


# ==================== 数据类 ====================


@dataclass
class CbBondInfo:
    """可转债双低计算结果"""
    ts_code: str
    bond_name: str
    trade_date: str
    bond_price: float           # 转债价格
    conv_price: float           # 转股价
    stock_price: float          # 正股价格
    premium_ratio: float        # 转股溢价率(%)
    dual_low: float             # 双低值
    vol: float                  # 成交量(手)
    stk_code: str = ''


@dataclass
class BacktestResult:
    """回测结果"""
    total_return: float = 0.0
    annual_return: float = 0.0
    max_drawdown: float = 0.0
    monthly_win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    num_trades: int = 0
    trade_log: list = field(default_factory=list)
    daily_nav: list = field(default_factory=list)


# ==================== 策略主类 ====================


class CbDualLowStrategy:
    """
    可转债双低策略

    双低值 = 转债价格 + 转股溢价率 × 1 (溢价率已以百分比表示)
    月频轮动，选最小值 Top N 等权持有
    """

    # 流动性过滤
    MIN_DAILY_VOL = 8000   # 最低成交量(手)，约800万成交额
    MIN_BOND_PRICE = 80.0  # 最低转债价格（止损底线）
    TOP_N_DEFAULT = 7      # 默认选债数量（手动操作友好）

    def __init__(self):
        pass

    # ==================== 核心计算 ====================

    def calculate_premium_ratio(self, bond_price: float,
                                conv_price: float,
                                stock_price: float) -> float:
        """
        计算转股溢价率

        公式:
            conversion_value = 100 / conv_price * stock_price
            premium_ratio = (bond_price / conversion_value - 1) * 100

        Returns:
            float: 转股溢价率(百分比)，例: 25.0 表示 25%
        """
        if conv_price is None or conv_price <= 0 or stock_price is None or stock_price <= 0:
            return float('inf')

        conversion_value = 100.0 / conv_price * stock_price
        if conversion_value <= 0:
            return float('inf')

        premium_ratio = (bond_price / conversion_value - 1.0) * 100.0
        return premium_ratio

    def calculate_dual_low(self, bond_price: float, premium_ratio: float) -> float:
        """
        计算双低值

        双低值 = 转债价格 + 转股溢价率(百分比)
        (如溢价率 25% = 25, 转债价 108 → 双低值 = 108 + 25 = 133)

        Returns:
            float: 双低值
        """
        return bond_price + premium_ratio

    # ==================== 数据获取 ====================

    def get_trading_dates(self) -> List[str]:
        """获取 cb_daily 表中的所有交易日期（降序）"""
        with get_session() as s:
            rows = s.execute(text("""
                SELECT DISTINCT trade_date FROM cb_daily
                ORDER BY trade_date ASC
            """)).fetchall()
        return [r[0] for r in rows]

    def get_month_end_dates(self, start: str, end: str) -> List[str]:
        """
        获取每月最后一个交易日（需有正股数据）

        Args:
            start: 开始日期 YYYYMMDD
            end: 结束日期 YYYYMMDD

        Returns:
            list: 每月末交易日列表
        """
        # 只取有正股数据的交易日
        query = text("""
            SELECT DISTINCT d.trade_date
            FROM cb_daily d
            JOIN cb_basic b ON d.ts_code = b.ts_code
            JOIN stock_daily_basic s ON b.stk_code = s.ts_code AND d.trade_date = s.trade_date
            WHERE d.trade_date BETWEEN :start AND :end
              AND b.delist_date IS NULL
              AND b.conv_price IS NOT NULL AND b.conv_price > 0
            ORDER BY d.trade_date
        """)
        with get_session() as s:
            rows = s.execute(query, {'start': start, 'end': end}).fetchall()
        dates = [r[0] for r in rows]

        # 按月分组取最后一天
        month_groups = {}
        for d in dates:
            month_key = d[:6]  # YYYYMM
            month_groups[month_key] = d  # 最后出现的覆盖之前的

        return sorted(month_groups.values())

    def get_bonds_for_date(self, trade_date: str) -> pd.DataFrame:
        """
        获取指定交易日所有可转债的双低计算数据

        SQL JOIN:
            cb_daily d + cb_basic b + stock_daily_basic s

        Returns:
            DataFrame with columns:
                ts_code, bond_name, bond_price, conv_price,
                stock_price, stock_close, vol
        """
        query = text("""
            SELECT
                d.ts_code,
                b.bond_short_name AS bond_name,
                b.stk_code,
                d.close AS bond_price,
                b.conv_price,
                s.close AS stock_close,
                d.vol,
                d.amount
            FROM cb_daily d
            JOIN cb_basic b ON d.ts_code = b.ts_code
            LEFT JOIN stock_daily_basic s
                ON b.stk_code = s.ts_code AND d.trade_date = s.trade_date
            WHERE d.trade_date = :date
              AND b.delist_date IS NULL
              AND b.conv_price IS NOT NULL AND b.conv_price > 0
              AND d.close IS NOT NULL AND d.close > :min_price
        """)

        with get_session() as s:
            rows = s.execute(query, {
                'date': trade_date,
                'min_price': self.MIN_BOND_PRICE
            }).fetchall()

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows, columns=[
            'ts_code', 'bond_name', 'stk_code', 'bond_price',
            'conv_price', 'stock_close', 'vol', 'amount'
        ])

        # 转换Decimal/其他数值类型为float
        for col in ['bond_price', 'conv_price', 'stock_close', 'vol', 'amount']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def get_daily_returns(self, codes: List[str], start_date: str,
                          end_date: str) -> pd.DataFrame:
        """
        获取指定转债在日期范围内的每日行情

        Returns:
            DataFrame: [trade_date, ts_code, close, pct_chg]
        """
        if not codes:
            return pd.DataFrame()

        # 逐日取数据（可能跨越数个月）
        query = text("""
            SELECT trade_date, ts_code, close, pct_chg
            FROM cb_daily
            WHERE ts_code IN :codes
              AND trade_date BETWEEN :start AND :end
            ORDER BY trade_date ASC
        """)

        with get_session() as s:
            rows = s.execute(query, {
                'codes': tuple(codes),
                'start': start_date,
                'end': end_date
            }).fetchall()

        return pd.DataFrame(rows, columns=['trade_date', 'ts_code', 'close', 'pct_chg'])

    # ==================== 推荐 ====================

    def get_recommendations(self, trade_date: str = None,
                            top_n: int = TOP_N_DEFAULT,
                            min_vol: float = MIN_DAILY_VOL) -> List[CbBondInfo]:
        """
        获取指定日期的可转债双低推荐清单

        Args:
            trade_date: 交易日 YYYYMMDD，默认取最新(有正股数据的)
            top_n: 推荐数量
            min_vol: 最低成交量(手)过滤

        Returns:
            List[CbBondInfo]: 按双低值升序排列
        """
        if trade_date is None:
            # 取最新有正股数据的交易日
            query = text("""
                SELECT MAX(d.trade_date) 
                FROM cb_daily d
                JOIN cb_basic b ON d.ts_code = b.ts_code
                JOIN stock_daily_basic s ON b.stk_code = s.ts_code AND d.trade_date = s.trade_date
                WHERE b.delist_date IS NULL
                  AND b.conv_price IS NOT NULL AND b.conv_price > 0
            """)
            with get_session() as s:
                trade_date = s.execute(query).scalar()
            if trade_date is None:
                return []

        df = self.get_bonds_for_date(trade_date)
        if df.empty:
            return []

        # 过滤: 正股价格必须有效
        df = df[df['stock_close'].notna() & (df['stock_close'] > 0)]
        if df.empty:
            return []

        # 过滤: 成交量
        if min_vol > 0:
            df = df[df['vol'] >= min_vol]

        # 计算转股溢价率和双低值
        df['premium_ratio'] = df.apply(
            lambda r: self.calculate_premium_ratio(
                r['bond_price'], r['conv_price'], r['stock_close']
            ), axis=1
        )

        # 过滤异常溢价率（负数或极大值通常表示数据异常）
        df = df[df['premium_ratio'] >= 0]
        df = df[df['premium_ratio'] < 200]  # 溢价率超过200%的转债太贵

        df['dual_low'] = df.apply(
            lambda r: self.calculate_dual_low(r['bond_price'], r['premium_ratio']),
            axis=1
        )

        # 按双低值排序取Top N
        df = df.sort_values('dual_low', ascending=True).head(top_n)

        results = []
        for _, r in df.iterrows():
            results.append(CbBondInfo(
                ts_code=r['ts_code'],
                bond_name=r['bond_name'],
                trade_date=trade_date,
                bond_price=round(float(r['bond_price']), 2),
                conv_price=round(float(r['conv_price']), 4),
                stock_price=round(float(r['stock_close']), 2),
                premium_ratio=round(float(r['premium_ratio']), 2),
                dual_low=round(float(r['dual_low']), 2),
                vol=int(r['vol']),
                stk_code=r['stk_code'],
            ))

        return results

    # ==================== 回测 ====================

    def backtest(self, start_date: str, end_date: str,
                 top_n: int = TOP_N_DEFAULT,
                 min_vol: float = MIN_DAILY_VOL,
                 initial_capital: float = 100000.0,
                 commission_rate: float = 0.0001) -> BacktestResult:
        """
        双低策略回测

        每月末按双低排序，下个交易日调仓。
        等权持有 Top N，每日跟踪净值。

        流程:
        1. 月末(calc_date)计算双低排序
        2. 次日(trade_date)执行调仓
        3. 持有至下月调仓日

        Args:
            start_date: 回测开始日期 YYYYMMDD
            end_date: 回测结束日期 YYYYMMDD
            top_n: 每期持有数量
            min_vol: 成交量过滤
            initial_capital: 初始资金
            commission_rate: 单边佣金率

        Returns:
            BacktestResult: 回测结果
        """
        month_ends = self.get_month_end_dates(start_date, end_date)
        if len(month_ends) < 2:
            return BacktestResult(num_trades=0)

        # 获取所有交易日（有正股数据的cb交易日）
        query = text("""
            SELECT DISTINCT d.trade_date
            FROM cb_daily d
            JOIN cb_basic b ON d.ts_code = b.ts_code
            JOIN stock_daily_basic s ON b.stk_code = s.ts_code AND d.trade_date = s.trade_date
            WHERE d.trade_date BETWEEN :start AND :end
              AND b.delist_date IS NULL
            ORDER BY d.trade_date
        """)
        with get_session() as s:
            rows = s.execute(query, {'start': start_date, 'end': end_date}).fetchall()
        all_dates = [r[0] for r in rows]

        if len(all_dates) < 2:
            return BacktestResult(num_trades=0)

        result = BacktestResult()
        cash = initial_capital
        positions = {}  # {ts_code: {'qty': int}}
        nav_log = []
        trade_log = []

        # 首日初始净值
        first_date = all_dates[0]
        nav_log.append({
            'date': first_date, 'nav': initial_capital,
            'cash': initial_capital, 'position_value': 0.0,
        })

        # 构建: 每个月末 -> 下个交易日(调仓日)的映射
        rebalance_schedule = []  # [(calc_date, trade_date)]
        for me in month_ends:
            # 找月末之后的下一个交易日
            next_dates = [d for d in all_dates if d > me]
            if next_dates:
                rebalance_schedule.append((me, next_dates[0]))

        if not rebalance_schedule:
            return BacktestResult(num_trades=0)

        # 第一笔交易: 使用第一个调仓日
        first_calc_date = rebalance_schedule[0][0]
        first_trade_date = rebalance_schedule[0][1]

        # 获取首日持仓的每日价格
        def _fill_daily_nav(start_d, end_d, pos, cash_amt, nav_list):
            """填充 start_d~end_d 之间的每日净值"""
            if not pos:
                return
            codes = list(pos.keys())
            daily_data = self.get_daily_returns(codes, start_d, end_d)
            if daily_data.empty:
                return
            daily_data['ts_code'] = daily_data['ts_code'].astype(str)
            for date in sorted(daily_data['trade_date'].unique()):
                day_prices = daily_data[daily_data['trade_date'] == date]
                pos_value = 0.0
                for _, row in day_prices.iterrows():
                    code = row['ts_code']
                    if code in pos:
                        pos_value += pos[code]['qty'] * float(row['close'])
                nav_list.append({
                    'date': date,
                    'nav': cash_amt + pos_value,
                    'cash': cash_amt,
                    'position_value': pos_value,
                })

        def _execute_trade(trade_d, calc_d, current_positions, current_cash):
            """根据 calc_d 的排序执行调仓"""
            recs = self.get_recommendations(calc_d, top_n, min_vol)
            selected = {r.ts_code for r in recs}
            if len(selected) < 1:
                return current_positions, current_cash

            # 获取调仓日价格（所有旧持仓+新选中）
            all_codes = set(current_positions.keys()) | selected
            price_q = text("SELECT ts_code, close FROM cb_daily WHERE trade_date = :d AND ts_code IN :codes")
            with get_session() as s:
                price_rows = s.execute(price_q, {
                    'd': trade_d,
                    'codes': tuple(all_codes) if len(all_codes) > 0 else ('__none__',)
                }).fetchall()
            price_map = {r[0]: float(r[1]) for r in price_rows}

            if not price_map:
                return current_positions, current_cash

            new_positions = {}

            # 保留仍在选中中的持仓
            for code in list(current_positions.keys()):
                if code in selected:
                    new_positions[code] = current_positions[code]
                else:
                    # 卖出不在新选中的
                    price = price_map.get(code, 0)
                    if price > 0:
                        qty = current_positions[code]['qty']
                        current_cash += qty * price * (1 - commission_rate)
                        trade_log.append({
                            'date': trade_d, 'action': 'SELL',
                            'code': code, 'price': price,
                            'qty': qty, 'value': qty * price,
                        })
                    del current_positions[code]

            # 买入新选中的（不包含已持有部分）
            already_held = set(new_positions.keys())
            need_to_buy = sorted(set(selected) - already_held)
            n_buy = len(need_to_buy)

            if n_buy > 0:
                per_bond = current_cash / n_buy
                for code in need_to_buy:
                    price = price_map.get(code, 0)
                    if price > 0:
                        qty = int(per_bond / price)
                        if qty > 0:
                            cost = qty * price * (1 + commission_rate)
                            if cost <= current_cash:
                                current_cash -= cost
                                new_positions[code] = {'qty': qty, 'cost': cost}
                                trade_log.append({
                                    'date': trade_d, 'action': 'BUY',
                                    'code': code, 'price': price,
                                    'qty': qty, 'value': cost,
                                })

            return new_positions, current_cash

        # === 首次建仓 ===
        positions, cash = _execute_trade(first_trade_date, first_calc_date, {}, cash)
        period_end = rebalance_schedule[1][1] if len(rebalance_schedule) > 1 else all_dates[-1]
        _fill_daily_nav(first_trade_date, period_end, positions, cash, nav_log)

        # === 后续轮次 ===
        for idx in range(1, len(rebalance_schedule)):
            calc_date, trade_date = rebalance_schedule[idx]

            if idx == len(rebalance_schedule) - 1:
                # 最后一期: 持有到结束
                next_trade = all_dates[-1]
            else:
                next_trade = rebalance_schedule[idx + 1][1]

            # 执行调仓
            positions, cash = _execute_trade(trade_date, calc_date, positions, cash)
            _fill_daily_nav(trade_date, next_trade, positions, cash, nav_log)

        # === 计算绩效 ===
        result.daily_nav = nav_log
        result.trade_log = trade_log
        result.num_trades = len(trade_log)

        if len(nav_log) > 1:
            navs = [n['nav'] for n in nav_log]
            dates = [n['date'] for n in nav_log]
            total_return = (navs[-1] / initial_capital - 1) * 100
            result.total_return = total_return

            days = (datetime.strptime(dates[-1], '%Y%m%d') -
                    datetime.strptime(dates[0], '%Y%m%d')).days
            if days > 0:
                result.annual_return = ((navs[-1] / initial_capital) ** (365.0 / days) - 1) * 100

            peak = navs[0]
            mdd = 0.0
            for nv in navs:
                if nv > peak:
                    peak = nv
                dd = (peak - nv) / peak * 100
                if dd > mdd:
                    mdd = dd
            result.max_drawdown = mdd

            # 月度胜率
            month_returns = {}
            for n in nav_log:
                mk = n['date'][:6]  # YYYYMM
                if mk not in month_returns:
                    month_returns[mk] = {'start': n['nav'], 'end': n['nav']}
                month_returns[mk]['end'] = n['nav']

            win_months = 0
            total_months = 0
            for mk in sorted(month_returns.keys()):
                mr = month_returns[mk]
                if mr['start'] > 0:
                    ret = (mr['end'] - mr['start']) / mr['start'] * 100
                    if ret > 0:
                        win_months += 1
                    total_months += 1

            result.monthly_win_rate = (win_months / total_months * 100) if total_months > 0 else 0

            # 夏普比（粗略估算）
            daily_returns = []
            for i in range(1, len(navs)):
                r = (navs[i] - navs[i - 1]) / navs[i - 1]
                daily_returns.append(r)

            if daily_returns:
                avg_ret = np.mean(daily_returns) * 252  # 年化
                std_ret = np.std(daily_returns) * np.sqrt(252)
                if std_ret > 0:
                    rf = 0.02  # 无风险利率 2%
                    result.sharpe_ratio = (avg_ret - rf) / std_ret

        return result


# ==================== 打印报告 ====================


def print_recommendations(recs: List[CbBondInfo]):
    """打印推荐清单"""
    if not recs:
        print("无推荐")
        return

    print(f"\n[CB] 双低推荐 Top {len(recs)} ({recs[0].trade_date[:4]}-{recs[0].trade_date[4:6]}-{recs[0].trade_date[6:]})")
    print(f"{'代码':<12} {'名称':<12} {'价格':>8} {'溢价率':>8} {'双低值':>8} {'成交量':>10}")
    print("-" * 56)
    for r in recs:
        print(f"{r.ts_code:<12} {r.bond_name:<12} "
              f"{r.bond_price:>8.2f} {r.premium_ratio:>7.1f}% "
              f"{r.dual_low:>8.2f} {r.vol:>10,}")


def print_backtest_result(result: BacktestResult):
    """打印回测结果"""
    print("\n" + "=" * 60)
    print("[CB] 双低策略回测结果")
    print("=" * 60)

    if result.num_trades == 0:
        print("  无交易记录")
        return

    print(f"  总收益率:     {result.total_return:>+8.2f}%")
    print(f"  年化收益率:   {result.annual_return:>+8.2f}%")
    print(f"  最大回撤:     {result.max_drawdown:>8.2f}%")
    print(f"  月度胜率:     {result.monthly_win_rate:>8.1f}%")
    print(f"  夏普比率:     {result.sharpe_ratio:>8.2f}")
    print(f"  交易次数:     {result.num_trades}")
    print(f"  运行天数:     {len(result.daily_nav)}")

    if len(result.daily_nav) > 1:
        first = result.daily_nav[0]
        last = result.daily_nav[-1]
        print(f"  净值: {first['nav']:.2f} -> {last['nav']:.2f}")


# ==================== CLI ====================

if __name__ == '__main__':
    import sys

    strategy = CbDualLowStrategy()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'recommend' or cmd == 'rec':
            date = sys.argv[2] if len(sys.argv) > 2 else None
            top_n = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            recs = strategy.get_recommendations(date, top_n)
            print_recommendations(recs)

        elif cmd == 'backtest' or cmd == 'bt':
            start = sys.argv[2] if len(sys.argv) > 2 else '20250701'
            end = sys.argv[3] if len(sys.argv) > 3 else '20260430'
            top_n = int(sys.argv[4]) if len(sys.argv) > 4 else 10
            result = strategy.backtest(start, end, top_n)
            print_backtest_result(result)

        elif cmd == 'dates':
            dates = strategy.get_trading_dates()
            print(f"交易日数: {len(dates)}")
            print(f"范围: {dates[0]} ~ {dates[-1]}")
            month_ends = strategy.get_month_end_dates(dates[0], dates[-1])
            print(f"月末日: {len(month_ends)} 天")
            for d in month_ends:
                print(f"  {d}")
        else:
            print(f"未知命令: {cmd}")
            print("用法: python analysis/cb_strategy.py [rec|backtest|dates]")
    else:
        # 默认: 打印最新推荐
        print("\n[CB] 可转债双低策略系统")
        recs = strategy.get_recommendations(top_n=10)
        print_recommendations(recs)
