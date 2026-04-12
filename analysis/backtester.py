"""
回测引擎

基于交易信号进行历史模拟交易，计算收益率、胜率、夏普比率等绩效指标，
支持多策略对比、交易成本和执行时机选择。
"""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd


class Backtester:
    """
    回测引擎

    交易逻辑:
    - 信号日T发出 BUY/SELL
    - execution_timing='close': T+1以收盘价执行 (默认)
    - execution_timing='open': T+1以开盘价执行 (更贴近实盘)
    - HOLD → 保持当前仓位不变

    交易成本:
    - commission_rate: 单边佣金率 (默认 万0.6 = 0.00006)
    - 买入和卖出各收一次佣金

    使用示例:
        bt = Backtester(commission_rate=0.00006, execution_timing='open')
        results = bt.run(df, signal_column='final_signal')
        bt.print_report(results)
    """

    def __init__(self, initial_capital: float = 100000,
                 commission_rate: float = 0.00006,
                 slippage: float = 0.0,
                 execution_timing: str = 'close'):
        """
        Args:
            initial_capital: 初始资金
            commission_rate: 单边佣金率 (万0.6 = 0.00006)
            slippage: 滑点 (预留扩展, 默认0)
            execution_timing: 执行时机 'close'(T+1收盘) / 'open'(T+1开盘)
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.execution_timing = execution_timing

    def run(self, df: pd.DataFrame, signal_column: str,
            position_series: Optional[pd.Series] = None) -> dict:
        """
        运行回测

        Args:
            df: 包含价格和信号列的 DataFrame
            signal_column: 信号列名 (值为 BUY/SELL/HOLD)
            position_series: 外部预计算的仓位序列 (0~1 浮点, 已含 T+1 延迟)
                             由 SmartPositionManager.generate_positions() 生成

        Returns:
            dict: 回测结果，包含绩效指标和交易明细
        """
        required_cols = ['trade_date', 'close', 'pct_chg', signal_column]
        if self.execution_timing == 'open':
            required_cols.append('open')

        bt_df = df[[c for c in required_cols if c in df.columns]].copy()
        bt_df = bt_df.dropna(subset=['close', 'pct_chg']).reset_index(drop=True)

        # 确保数值类型
        for col in ['close', 'pct_chg', 'open']:
            if col in bt_df.columns:
                bt_df[col] = pd.to_numeric(bt_df[col], errors='coerce')

        if len(bt_df) < 2:
            return self._empty_result()

        # 生成仓位序列
        if position_series is not None:
            positions = position_series.reset_index(drop=True)
            # 确保长度匹配
            if len(positions) != len(bt_df):
                positions = positions.iloc[:len(bt_df)]
        else:
            positions = self._generate_positions(bt_df[signal_column])

        # 计算每日收益（含交易成本）
        if self.execution_timing == 'open' and 'open' in bt_df.columns:
            daily_returns, total_commission = self._calc_returns_open(bt_df, positions)
        else:
            daily_returns, total_commission = self._calc_returns_close(bt_df, positions)

        portfolio_values = self.initial_capital * (1 + daily_returns).cumprod()

        # 买入持有基准
        benchmark_returns = bt_df['pct_chg'] / 100.0
        benchmark_values = self.initial_capital * (1 + benchmark_returns).cumprod()

        # 提取交易明细
        trades = self._extract_trades(bt_df, positions, signal_column)

        # 计算绩效指标
        metrics = self._calculate_metrics(
            portfolio_values, daily_returns, benchmark_values, benchmark_returns, trades
        )

        metrics['total_commission'] = round(total_commission, 2)
        metrics['commission_rate'] = self.commission_rate
        metrics['execution_timing'] = self.execution_timing
        metrics['portfolio_values'] = portfolio_values.tolist()
        metrics['benchmark_values'] = benchmark_values.tolist()
        metrics['trade_dates'] = bt_df['trade_date'].tolist()
        metrics['trades'] = trades
        metrics['signal_column'] = signal_column

        return metrics

    def _calc_returns_close(self, bt_df: pd.DataFrame, positions: pd.Series) -> tuple:
        """
        收盘价执行模式: T日信号 -> T+1收盘价买入/卖出
        收益基于 pct_chg (收盘价到收盘价)
        """
        daily_returns = positions * bt_df['pct_chg'] / 100.0

        # 计算交易成本
        position_changes = positions.diff().abs()
        position_changes.iloc[0] = positions.iloc[0]  # 第一天如果有仓位
        cost_per_change = self.commission_rate + self.slippage
        cost_series = position_changes * cost_per_change

        # 从日收益中扣除成本
        daily_returns = daily_returns - cost_series

        total_commission = (cost_series * self.initial_capital *
                           (1 + daily_returns.cumsum())).sum()
        # 简化计算总手续费
        total_commission = cost_series.sum() * self.initial_capital

        return daily_returns, total_commission

    def _calc_returns_open(self, bt_df: pd.DataFrame, positions: pd.Series) -> tuple:
        """
        开盘价执行模式: T日信号 -> T+1开盘价买入/卖出

        收益逻辑:
        - 持仓期间: 基于收盘价到收盘价的日涨跌幅
        - 买入当天: 收益 = (close - open) / open (当天开盘买入到收盘)
        - 卖出当天: 收益 = (open - prev_close) / prev_close (开盘卖出相对昨收)
        """
        n = len(bt_df)
        daily_returns = pd.Series(0.0, index=bt_df.index)

        prev_close = bt_df['close'].shift(1)

        for i in range(1, n):
            pos = positions.iloc[i]
            prev_pos = positions.iloc[i - 1]

            if pos == 1.0 and prev_pos == 0.0:
                # 买入日: 开盘价买入, 当天收益 = (close - open) / open
                open_price = bt_df.iloc[i]['open']
                close_price = bt_df.iloc[i]['close']
                if open_price > 0:
                    daily_returns.iloc[i] = (close_price - open_price) / open_price
            elif pos == 0.0 and prev_pos == 1.0:
                # 卖出日: 开盘价卖出, 收益 = (open - prev_close) / prev_close
                open_price = bt_df.iloc[i]['open']
                pc = prev_close.iloc[i]
                if pc > 0 and not np.isnan(pc):
                    daily_returns.iloc[i] = (open_price - pc) / pc
            elif pos == 1.0 and prev_pos == 1.0:
                # 持仓日: 正常收盘价到收盘价收益
                daily_returns.iloc[i] = bt_df.iloc[i]['pct_chg'] / 100.0

        # 计算交易成本
        position_changes = positions.diff().abs()
        position_changes.iloc[0] = positions.iloc[0]
        cost_per_change = self.commission_rate + self.slippage
        cost_series = position_changes * cost_per_change

        daily_returns = daily_returns - cost_series
        total_commission = cost_series.sum() * self.initial_capital

        return daily_returns, total_commission

    def compare_strategies(self, df: pd.DataFrame,
                           strategy_columns: Dict[str, str]) -> dict:
        """
        多策略对比回测

        Args:
            df: 包含多个信号列的 DataFrame
            strategy_columns: {策略名称: 信号列名}

        Returns:
            dict: 各策略的回测结果
        """
        results = {}
        for name, col in strategy_columns.items():
            if col in df.columns:
                results[name] = self.run(df, col)
            else:
                print(f"  警告: 信号列 '{col}' 不存在，跳过策略 '{name}'")

        # 添加买入持有基准
        results['买入持有'] = self._buy_and_hold(df)
        return results

    # ==================== 仓位生成 ====================

    def _generate_positions(self, signals: pd.Series) -> pd.Series:
        """
        将信号序列转换为仓位序列 (0或1)

        信号日T产生 → T+1执行 → 用 shift(1) 延迟
        """
        raw_positions = pd.Series(0.0, index=signals.index)
        position = 0.0

        for i in range(len(signals)):
            sig = signals.iloc[i]
            if sig == 'BUY':
                position = 1.0
            elif sig == 'SELL':
                position = 0.0
            raw_positions.iloc[i] = position

        # 延迟1天: T日信号 → T+1日才有仓位
        return raw_positions.shift(1).fillna(0.0)

    # ==================== 交易明细 ====================

    def _extract_trades(self, bt_df: pd.DataFrame, positions: pd.Series,
                        signal_column: str) -> List[dict]:
        """提取完整的买卖交易对（含手续费, 支持连续仓位 0~1）"""
        trades = []
        entry_idx = None
        entry_price = None

        cost_rate = self.commission_rate + self.slippage

        for i in range(1, len(positions)):
            prev_pos = positions.iloc[i - 1]
            curr_pos = positions.iloc[i]

            # 从空仓到持仓 = 买入 (支持 0→0.3, 0→1.0 等)
            if curr_pos > 0 and prev_pos <= 0:
                entry_idx = i
                if self.execution_timing == 'open' and 'open' in bt_df.columns:
                    entry_price = bt_df.iloc[i]['open']
                else:
                    entry_price = bt_df.iloc[i]['close']
            # 从持仓到空仓 = 卖出 (支持 0.5→0, 1.0→0 等)
            elif curr_pos <= 0 and prev_pos > 0:
                if entry_idx is not None and entry_price is not None:
                    if self.execution_timing == 'open' and 'open' in bt_df.columns:
                        exit_price = bt_df.iloc[i]['open']
                    else:
                        exit_price = bt_df.iloc[i]['close']

                    # 扣除双边手续费
                    net_entry = entry_price * (1 + cost_rate)
                    net_exit = exit_price * (1 - cost_rate)
                    pnl = (net_exit - net_entry) / net_entry

                    trades.append({
                        'entry_date': str(bt_df.iloc[entry_idx]['trade_date']),
                        'exit_date': str(bt_df.iloc[i]['trade_date']),
                        'entry_price': round(entry_price, 2),
                        'exit_price': round(exit_price, 2),
                        'return_pct': round(pnl * 100, 2),
                        'holding_days': i - entry_idx,
                    })
                    entry_idx = None
                    entry_price = None

        # 如果最后仍然持仓，用最后一天的价格结算
        if entry_idx is not None and entry_price is not None:
            if self.execution_timing == 'open' and 'open' in bt_df.columns:
                last_price = bt_df.iloc[-1]['close']  # 未平仓用收盘价
            else:
                last_price = bt_df.iloc[-1]['close']

            net_entry = entry_price * (1 + cost_rate)
            net_exit = last_price * (1 - cost_rate)
            pnl = (net_exit - net_entry) / net_entry

            trades.append({
                'entry_date': str(bt_df.iloc[entry_idx]['trade_date']),
                'exit_date': str(bt_df.iloc[-1]['trade_date']),
                'entry_price': round(entry_price, 2),
                'exit_price': round(last_price, 2),
                'return_pct': round(pnl * 100, 2),
                'holding_days': len(bt_df) - 1 - entry_idx,
                'open': True,  # 标记为未平仓
            })

        return trades

    # ==================== 绩效计算 ====================

    def _calculate_metrics(self, portfolio_values: pd.Series,
                           daily_returns: pd.Series,
                           benchmark_values: pd.Series,
                           benchmark_returns: pd.Series,
                           trades: List[dict]) -> dict:
        """计算所有绩效指标"""
        trading_days = len(portfolio_values)
        final_value = portfolio_values.iloc[-1]
        bm_final = benchmark_values.iloc[-1]

        total_return = (final_value - self.initial_capital) / self.initial_capital
        bm_total_return = (bm_final - self.initial_capital) / self.initial_capital

        annualized_return = self._annualized_return(total_return, trading_days)
        bm_annualized = self._annualized_return(bm_total_return, trading_days)

        max_drawdown = self._max_drawdown(portfolio_values)
        bm_max_drawdown = self._max_drawdown(benchmark_values)

        sharpe = self._sharpe_ratio(daily_returns)
        bm_sharpe = self._sharpe_ratio(benchmark_returns)

        # 交易统计
        closed_trades = [t for t in trades if not t.get('open', False)]
        winning = [t for t in closed_trades if t['return_pct'] > 0]
        losing = [t for t in closed_trades if t['return_pct'] <= 0]

        win_rate = len(winning) / len(closed_trades) if closed_trades else 0
        avg_win = np.mean([t['return_pct'] for t in winning]) if winning else 0
        avg_loss = abs(np.mean([t['return_pct'] for t in losing])) if losing else 0
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')

        # 交易操作次数（买+卖）
        trade_operations = len(closed_trades) * 2
        open_trades = [t for t in trades if t.get('open', False)]
        if open_trades:
            trade_operations += len(open_trades)  # 只有买入

        return {
            'total_return': round(total_return * 100, 2),
            'annualized_return': round(annualized_return * 100, 2),
            'max_drawdown': round(max_drawdown * 100, 2),
            'sharpe_ratio': round(sharpe, 2),
            'win_rate': round(win_rate * 100, 1),
            'profit_loss_ratio': round(profit_loss_ratio, 2),
            'trade_count': len(closed_trades),
            'trade_operations': trade_operations,
            'avg_win_pct': round(avg_win, 2),
            'avg_loss_pct': round(avg_loss, 2),
            'final_value': round(final_value, 2),
            'benchmark_total_return': round(bm_total_return * 100, 2),
            'benchmark_annualized': round(bm_annualized * 100, 2),
            'benchmark_max_drawdown': round(bm_max_drawdown * 100, 2),
            'benchmark_sharpe': round(bm_sharpe, 2),
            'excess_return': round((total_return - bm_total_return) * 100, 2),
            'trading_days': trading_days,
        }

    @staticmethod
    def _annualized_return(total_return: float, trading_days: int) -> float:
        if trading_days <= 0:
            return 0.0
        return (1 + total_return) ** (252 / trading_days) - 1

    @staticmethod
    def _max_drawdown(values: pd.Series) -> float:
        peak = values.expanding(min_periods=1).max()
        drawdown = (values - peak) / peak
        return abs(drawdown.min())

    @staticmethod
    def _sharpe_ratio(daily_returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        if daily_returns.std() == 0:
            return 0.0
        excess = daily_returns.mean() - risk_free_rate / 252
        return excess / daily_returns.std() * np.sqrt(252)

    # ==================== 买入持有基准 ====================

    def _buy_and_hold(self, df: pd.DataFrame) -> dict:
        """买入持有基准回测（含买入卖出各一次手续费）"""
        bt_df = df[['trade_date', 'close', 'pct_chg']].copy()
        bt_df = bt_df.dropna(subset=['close', 'pct_chg']).reset_index(drop=True)

        if len(bt_df) < 2:
            return self._empty_result()

        daily_returns = bt_df['pct_chg'] / 100.0

        # 买入持有: 首日扣买入佣金, 末日扣卖出佣金
        cost_rate = self.commission_rate + self.slippage
        daily_returns.iloc[0] = daily_returns.iloc[0] - cost_rate
        daily_returns.iloc[-1] = daily_returns.iloc[-1] - cost_rate

        portfolio_values = self.initial_capital * (1 + daily_returns).cumprod()
        trading_days = len(portfolio_values)
        final_value = portfolio_values.iloc[-1]

        total_return = (final_value - self.initial_capital) / self.initial_capital
        total_commission = 2 * cost_rate * self.initial_capital

        return {
            'total_return': round(total_return * 100, 2),
            'annualized_return': round(self._annualized_return(total_return, trading_days) * 100, 2),
            'max_drawdown': round(self._max_drawdown(portfolio_values) * 100, 2),
            'sharpe_ratio': round(self._sharpe_ratio(daily_returns), 2),
            'win_rate': 0,
            'profit_loss_ratio': 0,
            'trade_count': 1,
            'trade_operations': 2,
            'trading_days': trading_days,
            'final_value': round(final_value, 2),
            'total_commission': round(total_commission, 2),
            'commission_rate': self.commission_rate,
            'execution_timing': self.execution_timing,
            'signal_column': 'buy_and_hold',
        }

    @staticmethod
    def _empty_result() -> dict:
        return {
            'total_return': 0, 'annualized_return': 0, 'max_drawdown': 0,
            'sharpe_ratio': 0, 'win_rate': 0, 'profit_loss_ratio': 0,
            'trade_count': 0, 'trade_operations': 0, 'trading_days': 0,
            'final_value': 0, 'total_commission': 0,
        }

    # ==================== 报告输出 ====================

    def print_report(self, results: dict, index_name: str = ''):
        """打印单策略回测报告"""
        print(f"\n{'=' * 60}")
        title = f"  {index_name} 回测报告" if index_name else "  回测报告"
        print(title)
        print(f"{'=' * 60}")

        timing_text = '收盘价' if results.get('execution_timing', 'close') == 'close' else '开盘价'
        comm_text = f"万{results.get('commission_rate', 0) * 10000:.1f}"

        print(f"  回测天数: {results.get('trading_days', 0)} | "
              f"初始资金: {self.initial_capital:,.0f} | "
              f"执行: T+1{timing_text} | 佣金: {comm_text}")

        print(f"\n  【策略绩效】")
        print(f"    总收益率:     {results.get('total_return', 0):+.2f}%")
        print(f"    年化收益率:   {results.get('annualized_return', 0):+.2f}%")
        print(f"    最大回撤:     -{results.get('max_drawdown', 0):.2f}%")
        print(f"    夏普比率:     {results.get('sharpe_ratio', 0):.2f}")
        print(f"    胜率:         {results.get('win_rate', 0):.1f}%")
        print(f"    盈亏比:       {results.get('profit_loss_ratio', 0):.2f}")
        print(f"    交易次数:     {results.get('trade_count', 0)}")

        if results.get('total_commission', 0) > 0:
            print(f"    手续费合计:   {results.get('total_commission', 0):,.2f} "
                  f"({results.get('trade_operations', 0)} 次买卖操作)")

        if 'benchmark_total_return' in results:
            print(f"\n  【基准对比 (买入持有)】")
            print(f"    基准收益:     {results.get('benchmark_total_return', 0):+.2f}%")
            print(f"    超额收益:     {results.get('excess_return', 0):+.2f}%")
            print(f"    基准最大回撤: -{results.get('benchmark_max_drawdown', 0):.2f}%")

        if results.get('trade_count', 0) > 0:
            print(f"\n  【交易统计】")
            print(f"    平均盈利:     +{results.get('avg_win_pct', 0):.2f}%")
            print(f"    平均亏损:     -{results.get('avg_loss_pct', 0):.2f}%")

        print(f"{'=' * 60}\n")

    def print_comparison(self, comparison: dict, index_name: str = ''):
        """打印多策略对比报告"""
        print(f"\n{'=' * 80}")
        title = f"  {index_name} 多策略对比" if index_name else "  多策略对比"
        print(title)

        # 显示回测配置
        timing_text = '收盘价' if self.execution_timing == 'close' else '开盘价'
        comm_text = f"万{self.commission_rate * 10000:.1f}"
        print(f"  执行: T+1{timing_text} | 佣金: {comm_text}")

        print(f"{'=' * 80}")

        header = (f"  {'策略':<12} {'总收益':>8} {'年化收益':>8} {'最大回撤':>8} "
                  f"{'夏普':>6} {'胜率':>6} {'交易数':>6} {'手续费':>8}")
        print(header)
        print(f"  {'-' * 74}")

        for name, result in comparison.items():
            tr = result.get('total_return', 0)
            ar = result.get('annualized_return', 0)
            md = result.get('max_drawdown', 0)
            sr = result.get('sharpe_ratio', 0)
            wr = result.get('win_rate', 0)
            tc = result.get('trade_count', 0)
            comm = result.get('total_commission', 0)

            print(f"  {name:<12} {tr:>+7.1f}% {ar:>+7.1f}% {md:>7.1f}% "
                  f"{sr:>6.2f} {wr:>5.1f}% {tc:>6d} {comm:>7.0f}")

        print(f"{'=' * 80}\n")


