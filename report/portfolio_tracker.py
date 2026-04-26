"""
组合持仓跟踪器

基于每日信号管理实际持仓状态（成本、市值、操作），存入MySQL。
每日流程：读取昨日持仓 → 价格漂移 → 信号分析 → 操作 → 写入今日持仓
"""
import sys
import os
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from sqlalchemy import desc

from mysql_connect.db import get_session
from entity.models.portfolio_state import PortfolioState


# ============================================================
# 核心常量
# ============================================================

# 可用指数列表（不含上证综指，已排除）
TRACKED_CODES = [
    '000688.SH',  # 科创50
    '000905.SH',  # 中证500
    '399006.SZ',  # 创业板指
    '399001.SZ',  # 深证成指
    '000300.SH',  # 沪深300
    '000016.SH',  # 上证50
    '000852.SH',  # 中证1000
]

# 指数名称映射
TS_CODE_NAME = {
    '000688.SH': '科创50',
    '000905.SH': '中证500',
    '399006.SZ': '创业板指',
    '399001.SZ': '深证成指',
    '000300.SH': '沪深300',
    '000016.SH': '上证50',
    '000852.SH': '中证1000',
}


class PortfolioTracker:
    """
    组合持仓跟踪器

    使用示例:
        tracker = PortfolioTracker()
        # 首次运行 - 初始化持仓
        tracker.init_positions([
            {'ts_code': '000688.SH', 'name': '科创50', 'cost_basis': 6725, 'market_value': 7655},
            ...
        ])
        # 每日更新
        tracker.daily_update(signals_list)
        # 获取最新状态
        latest = tracker.get_latest_state()
    """

    # ---------- 初始化 ----------

    def init_positions(self, positions: List[Dict], trade_date: date = None) -> bool:
        """
        首次初始化持仓（仅当 portfolio_state 表为空时有效）

        Args:
            positions: [{'ts_code','name','cost_basis','market_value'}, ...]
            trade_date: 起始日期，默认今天

        Returns:
            bool: 是否成功写入
        """
        # 检查是否已有记录
        with get_session() as session:
            exists = session.query(PortfolioState).first()
            if exists:
                print("[SKIP] portfolio_state 已有数据，跳过初始化")
                return False

        if trade_date is None:
            trade_date = date.today()

        total_mv = Decimal('0.00')
        total_cost = Decimal('0.00')
        rows = []

        for p in positions:
            cost = Decimal(str(p.get('cost_basis', 0)))
            mv = Decimal(str(p.get('market_value', 0)))
            total_cost += cost
            total_mv += mv
            rows.append({'ts_code': p['ts_code'], 'name': p.get('name', ''), 'cost': cost, 'mv': mv})

        # 计算权重和收益率
        with get_session() as session:
            for r in rows:
                weight = (r['mv'] / total_mv * Decimal('100')) if total_mv > 0 else Decimal('0')
                ret = ((r['mv'] - r['cost']) / r['cost'] * Decimal('100')) if r['cost'] > 0 else Decimal('0')
                cash_pct = Decimal('0')  # 首次初始化，假设满仓
                total_position_pct = Decimal('100')

                rec = PortfolioState(
                    trade_date=trade_date,
                    ts_code=r['ts_code'],
                    name=r['name'],
                    cost_basis=r['cost'],
                    market_value=r['mv'],
                    weight_pct=weight,
                    return_pct=ret,
                    current_signal='INIT',
                    action='建仓',
                    action_value=Decimal('0'),
                    new_market_value=r['mv'],
                    new_weight_pct=weight,
                    total_position_pct=total_position_pct,
                    total_market_value=total_mv,
                    cash_pct=cash_pct,
                )
                session.add(rec)

        print(f"[OK] 持仓初始化完成: {len(rows)} 个指数, 总市值 {total_mv:,.2f} RMB, 日期 {trade_date}")
        return True

    # ---------- 每日更新 ----------

    def daily_update(self, signals_list: List[Dict], trade_date: date = None) -> Dict:
        """
        每日持仓更新：价格漂移 → 信号 → 操作 → 写入

        Args:
            signals_list: 来自 IndexAnalyzer.get_current_signal() 的信号列表
            trade_date: 交易日，默认今天

        Returns:
            summary: 操作汇总字典
        """
        if trade_date is None:
            trade_date = date.today()

        # 1. 读取昨日持仓
        prev_positions = self._get_latest_positions()
        if not prev_positions:
            print("[WARNING] 无历史持仓数据，跳过 daily_update")
            return {'status': 'skip', 'reason': 'no_history'}

        # 2. 建立信号映射 {ts_code: signal_dict}
        signal_map = {}
        for sig in signals_list:
            code = sig.get('ts_code', '')
            signal_map[code] = sig

        # 3. 计算价格漂移 + 信号操作
        today_rows = []
        total_mv_after = Decimal('0.00')
        total_cost = Decimal('0.00')
        operations = []

        # 昨日总市值（含现金）
        prev_total_mv = prev_positions.get('_total_mv', Decimal('0'))
        prev_cash_mv = prev_positions.get('_cash_mv', Decimal('0'))

        # 逐指数处理 - 仅跟踪已有持仓的指数
        tracked_in_db = [k for k in prev_positions.keys()
                        if k not in ('_total_mv', '_cash_mv', '_cash_pct')]
        for code in tracked_in_db:
            prev = prev_positions[code]
            sig = signal_map.get(code, {})

            name = TS_CODE_NAME.get(code, code)
            prev_cost = prev.get('cost', Decimal('0'))
            prev_mv = prev.get('mv', Decimal('0'))
            prev_weight = prev.get('weight', Decimal('0'))

            # 涨跌幅
            pct_chg = Decimal(str(sig.get('pct_chg', 0))) if sig else Decimal('0')

            # 价格漂移
            drifted_mv = prev_mv * (Decimal('1') + pct_chg / Decimal('100'))

            # 信号
            signal = sig.get('final_signal', 'HOLD') if sig else 'HOLD'
            confidence = Decimal(str(sig.get('final_confidence', 0.5))) if sig else Decimal('0.5')
            strength = Decimal(str(sig.get('signal_strength', 0))) if sig else Decimal('0')
            factor_score = Decimal(str(sig.get('factor_score', 50))) if sig else Decimal('50')

            # 操作判定
            action, action_value = self._calc_action(signal, confidence, drifted_mv, prev_cost, prev_weight)

            # 操作后市值
            new_mv = drifted_mv + action_value
            total_cost += prev_cost + (action_value if action_value > 0 else Decimal('0'))
            total_mv_after += new_mv

            if action != '持有':
                operations.append({
                    'ts_code': code,
                    'name': name,
                    'action': action,
                    'value': action_value,
                    'old_mv': drifted_mv,
                    'new_mv': new_mv,
                })

            today_rows.append({
                'ts_code': code,
                'name': name,
                'cost': prev_cost + (action_value if action_value > 0 else Decimal('0')),
                'old_mv': prev_mv,
                'drifted_mv': drifted_mv,
                'new_mv': new_mv,
                'signal': signal,
                'strength': strength,
                'confidence': confidence,
                'factor_score': factor_score,
                'action': action,
                'action_value': action_value,
                'pct_chg': pct_chg,
            })

        # 现金变化
        total_cash_inflow = sum(r['action_value'] for r in today_rows if r['action_value'] < 0)  # 卖出回流现金
        total_cash_outflow = sum(r['action_value'] for r in today_rows if r['action_value'] > 0)  # 买入消耗现金
        cash_mv = prev_cash_mv + abs(total_cash_inflow) - total_cash_outflow
        if cash_mv < Decimal('0'):
            cash_mv = Decimal('0')

        grand_total = total_mv_after + cash_mv

        # 写数据库 - upsert (存在则更新, 不存在则插入)
        from sqlalchemy import and_
        with get_session() as session:
            for r in today_rows:
                weight = (r['new_mv'] / grand_total * Decimal('100')) if grand_total > 0 else Decimal('0')
                ret = ((r['new_mv'] - r['cost']) / r['cost'] * Decimal('100')) if r['cost'] > 0 else Decimal('0')

                # 检查是否已有该日该指数的记录
                existing = session.query(PortfolioState).filter(
                    and_(
                        PortfolioState.trade_date == trade_date,
                        PortfolioState.ts_code == r['ts_code']
                    )
                ).first()

                if existing:
                    # 更新
                    existing.cost_basis = r['cost']
                    existing.market_value = r['new_mv']
                    existing.weight_pct = weight
                    existing.return_pct = ret
                    existing.current_signal = r['signal']
                    existing.signal_strength = r['strength']
                    existing.confidence = r['confidence']
                    existing.factor_score = r['factor_score']
                    existing.action = r['action']
                    existing.action_value = r['action_value']
                    existing.new_market_value = r['new_mv']
                    existing.new_weight_pct = weight
                    existing.total_position_pct = (total_mv_after / grand_total * Decimal('100')) if grand_total > 0 else Decimal('0')
                    existing.total_market_value = grand_total
                    existing.cash_pct = (cash_mv / grand_total * Decimal('100')) if grand_total > 0 else Decimal('100')
                else:
                    # 插入
                    rec = PortfolioState(
                        trade_date=trade_date,
                        ts_code=r['ts_code'],
                        name=r['name'],
                        cost_basis=r['cost'],
                        market_value=r['new_mv'],
                        weight_pct=weight,
                        return_pct=ret,
                        current_signal=r['signal'],
                        signal_strength=r['strength'],
                        confidence=r['confidence'],
                        factor_score=r['factor_score'],
                        action=r['action'],
                        action_value=r['action_value'],
                        new_market_value=r['new_mv'],
                        new_weight_pct=weight,
                        total_position_pct=(total_mv_after / grand_total * Decimal('100')) if grand_total > 0 else Decimal('0'),
                        total_market_value=grand_total,
                        cash_pct=(cash_mv / grand_total * Decimal('100')) if grand_total > 0 else Decimal('100'),
                    )
                    session.add(rec)

        summary = {
            'status': 'ok',
            'trade_date': str(trade_date),
            'total_mv': float(grand_total),
            'position_pct': float(total_mv_after / grand_total * 100) if grand_total > 0 else 0,
            'cash_pct': float(cash_mv / grand_total * 100) if grand_total > 0 else 100,
            'operations': [
                {'name': op['name'], 'action': op['action'], 'value': float(op['value'])}
                for op in operations
            ],
            'buy_count': sum(1 for op in operations if op['action'] in ('建仓', '加仓')),
            'sell_count': sum(1 for op in operations if op['action'] in ('减仓', '清仓')),
        }
        return summary

    # ---------- 操作计算 ----------

    @staticmethod
    def _calc_action(signal: str, confidence: Decimal, drifted_mv: Decimal,
                     cost_basis: Decimal, weight_pct: Decimal) -> Tuple[str, Decimal]:
        """
        信号 → 具体操作

        Rules:
            - BUY: 权重<5%建仓(confidence×5000元), 权重≥5%加仓(confidence×2000元)
            - SELL: 减仓50% (市值减半)
            - HOLD: 不变

        Returns:
            (action_name, action_value)  action_value 正=买入, 负=卖出
        """
        if signal == 'BUY':
            if weight_pct < Decimal('5') or drifted_mv < Decimal('100'):
                # 建仓
                invest = confidence * Decimal('5000')
                action_value = invest.quantize(Decimal('0.01'))
                return ('建仓', action_value)
            else:
                # 加仓
                invest = confidence * Decimal('2000')
                action_value = invest.quantize(Decimal('0.01'))
                return ('加仓', action_value)

        elif signal == 'SELL':
            if drifted_mv <= Decimal('100'):
                return ('清仓', -drifted_mv)
            else:
                sell_value = (drifted_mv / Decimal('2')).quantize(Decimal('0.01'))
                return ('减仓', -sell_value)

        else:  # HOLD
            return ('持有', Decimal('0'))

    # ---------- 查询 ----------

    def _get_latest_positions(self) -> Optional[Dict]:
        """获取最近一天的持仓数据，返回 {ts_code: {mv,cost,weight}, _total_mv, _cash_mv}"""
        with get_session() as session:
            # 找最新交易日
            latest_date = session.query(PortfolioState.trade_date).order_by(
                desc(PortfolioState.trade_date)).first()
            if not latest_date:
                return None

            records = session.query(PortfolioState).filter(
                PortfolioState.trade_date == latest_date[0]).all()

            result = {}
            for rec in records:
                result[rec.ts_code] = {
                    'mv': rec.market_value or Decimal('0'),
                    'cost': rec.cost_basis or Decimal('0'),
                    'weight': rec.weight_pct or Decimal('0'),
                }
                result['_total_mv'] = rec.total_market_value or Decimal('0')
                result['_cash_pct'] = rec.cash_pct or Decimal('0')

            # 计算现金市值
            total_mv = result.get('_total_mv', Decimal('0'))
            position_mv = sum(r['mv'] for r in result.values() if isinstance(r, dict) and 'mv' in r)
            result['_cash_mv'] = total_mv - position_mv

            return result

    def get_latest_state(self) -> List[Dict]:
        """获取最新交易日所有持仓记录（给报表用）"""
        with get_session() as session:
            latest_date = session.query(PortfolioState.trade_date).order_by(
                desc(PortfolioState.trade_date)).first()
            if not latest_date:
                return []

            records = session.query(PortfolioState).filter(
                PortfolioState.trade_date == latest_date[0]).order_by(
                PortfolioState.weight_pct.desc()).all()

            return [r.to_dict() for r in records]

    def get_prev_state(self, days_ago: int = 1) -> List[Dict]:
        """获取前N天持仓记录"""
        with get_session() as session:
            dates = session.query(PortfolioState.trade_date).distinct().order_by(
                desc(PortfolioState.trade_date)).limit(days_ago + 1).all()
            if len(dates) <= days_ago:
                return []
            target_date = dates[days_ago][0]

            records = session.query(PortfolioState).filter(
                PortfolioState.trade_date == target_date).all()
            return [r.to_dict() for r in records]

    def summary_text(self, state: List[Dict] = None) -> str:
        """生成持仓摘要文本"""
        if state is None:
            state = self.get_latest_state()
        if not state:
            return "[无持仓数据]"

        lines = []
        lines.append("-" * 60)
        lines.append(f"[持仓概览] 日期: {state[0].get('trade_date', 'N/A')}")
        lines.append("-" * 60)

        total_pct = float(state[0].get('total_position_pct', 0))
        cash_pct = float(state[0].get('cash_pct', 0))
        total_mv = float(state[0].get('total_market_value', 0))
        lines.append(f"总仓位: {total_pct:.1f}%  |  现金: {cash_pct:.1f}%  |  总市值: RMB{total_mv:,.2f}")
        lines.append("")

        # 找到今日有操作的记录
        has_action = any(r.get('action') not in ('持有', None, 'INIT') for r in state)
        if has_action:
            lines.append("今日操作:")
            for r in state:
                action = r.get('action', '')
                if action and action not in ('持有', 'INIT', None):
                    mv_before = float(r.get('market_value', 0)) + abs(float(r.get('action_value', 0)))
                    if r.get('action_value', 0) < 0:
                        mv_before = float(r.get('market_value', 0)) - abs(float(r.get('action_value', 0)))
                    action_str = f"  {r.get('name',''):8s}  {action}  RMB{abs(float(r.get('action_value',0))):>8.2f}"
                    lines.append(action_str)
            lines.append("")

        lines.append(f"{'指数':8s} {'权重':>7s} {'市值':>10s} {'成本':>10s} {'收益%':>7s} {'信号':>6s} {'强度':>6s}")
        lines.append("-" * 60)
        for r in state:
            name = r.get('name', '')
            w = float(r.get('weight_pct', 0))
            mv = float(r.get('market_value', 0))
            cost = float(r.get('cost_basis', 0))
            ret = float(r.get('return_pct', 0))
            sig = r.get('current_signal', '')
            strength = float(r.get('signal_strength', 0))
            lines.append(f"{name:8s} {w:6.1f}% RMB{mv:>8,.0f} RMB{cost:>8,.0f} {ret:>+6.2f}% {sig:>6s} {strength:>+5.1f}")

        lines.append("-" * 60)
        return '\n'.join(lines)
