"""
投资计划生成器 InvestmentPlanner

在信号分析(IndexAnalyzer)和持仓执行(PortfolioTracker)之间，
根据可用资金、信号优先级、市场状态，生成最优投资操作计划。

核心逻辑:
1. SELL信号始终优先执行 → 释放现金
2. BUY信号按优先级排序 → 依次分配可用现金
3. 保留最低现金储备 (min_cash_reserve)
4. HOLD → 维持不变，不占用现金
"""

from decimal import Decimal
from typing import List, Dict, Optional, Tuple


# ============================================================
# 默认参数
# ============================================================

# 最低现金储备比例 (保留作为应急/抄底)
MIN_CASH_RESERVE_RATIO = Decimal('0.10')  # 10%

# 趋势状态 → 买入优先级乘数
TREND_MULTIPLIER = {
    'rising':    Decimal('1.3'),   # 上升趋势 → 顺势加仓
    'sideways':  Decimal('1.0'),   # 震荡 → 中性
    'falling':   Decimal('0.3'),   # 下降趋势 → 避免买入
}

# 操作比例 (相对 TOTAL_CAPITAL)
RATIO_OPEN  = Decimal('0.10')   # 新开仓: 10% 本金
RATIO_ADD   = Decimal('0.04')   # 加仓:    4%  本金


def calc_priority_score(signal_dict: Dict) -> float:
    """
    计算BUY信号的优先级得分 (越高越优先买入)

    公式:
        priority = confidence × (factor_score / 50) × trend_multiplier

    Args:
        signal_dict: 单个指数的信号字典

    Returns:
        priority_score: 0~2.6 之间的浮点数
    """
    confidence = float(signal_dict.get('final_confidence', 0.5))
    factor_score = float(signal_dict.get('factor_score', 50))
    trend = signal_dict.get('trend_state', 'sideways')

    # 趋势乘数
    trend_mult = float(TREND_MULTIPLIER.get(trend, Decimal('1.0')))

    # 因子评分归一化 (50分=基准1.0, 80分=1.6, 30分=0.6)
    factor_norm = factor_score / 50.0

    score = confidence * factor_norm * trend_mult
    return round(score, 4)


def calc_desired_amount(signal_dict: Dict, existing_mv: Decimal) -> Decimal:
    """
    计算理想买入/卖出金额

    Args:
        signal_dict: 信号字典
        existing_mv: 当前持仓市值

    Returns:
        desired_amount: 正=买入, 负=卖出, 0=不动
    """
    signal = signal_dict.get('final_signal', 'HOLD')
    confidence = Decimal(str(signal_dict.get('final_confidence', 0.5)))
    from report.portfolio_tracker import TOTAL_CAPITAL

    if signal == 'BUY':
        if existing_mv < Decimal('100'):
            # 新开仓: confidence × 10% × TOTAL_CAPITAL
            return (confidence * TOTAL_CAPITAL * RATIO_OPEN).quantize(Decimal('0.01'))
        else:
            # 加仓: confidence × 4% × TOTAL_CAPITAL
            return (confidence * TOTAL_CAPITAL * RATIO_ADD).quantize(Decimal('0.01'))

    elif signal == 'SELL':
        if existing_mv <= Decimal('100'):
            return -existing_mv  # 清仓
        else:
            return -(existing_mv / Decimal('2')).quantize(Decimal('0.01'))  # 减半

    else:  # HOLD
        return Decimal('0')


def plan_investments(signals_list: List[Dict],
                     current_positions: Dict,
                     available_cash: Decimal,
                     total_capital: Decimal,
                     min_cash_reserve: Decimal = None) -> Tuple[List[Dict], Decimal]:
    """
    生成投资操作计划

    Args:
        signals_list: 所有指数的信号列表
        current_positions: 当前持仓 {ts_code: {'mv': Decimal, 'weight': Decimal}}
        available_cash: 当前可用现金
        total_capital: 总本金
        min_cash_reserve: 最低现金保留金额 (默认 10% × total_capital)

    Returns:
        (operations, cash_after):
            operations: [{'ts_code','name','action','value','priority'}, ...]
            cash_after: 操作后剩余现金
    """
    from report.portfolio_tracker import TS_CODE_NAME

    if min_cash_reserve is None:
        min_cash_reserve = total_capital * MIN_CASH_RESERVE_RATIO

    operations = []
    remaining_cash = available_cash

    # ----- 第一步：处理 SELL 信号 (始终执行) -----
    for sig in signals_list:
        code = sig.get('ts_code', '')
        signal = sig.get('final_signal', 'HOLD')
        if signal != 'SELL':
            continue

        existing_mv = current_positions.get(code, {}).get('mv', Decimal('0'))
        name = TS_CODE_NAME.get(code, sig.get('name', code))
        amount = calc_desired_amount(sig, existing_mv)

        operations.append({
            'ts_code': code,
            'name': name,
            'action': '减仓' if existing_mv > Decimal('100') else '清仓',
            'value': amount,  # 负数
            'priority': 999,  # SELL 最高优先级
        })
        remaining_cash += abs(amount)  # 卖出释放现金

    # ----- 第二步：计算 BUY 信号的优先级 -----
    buy_signals = []
    for sig in signals_list:
        code = sig.get('ts_code', '')
        signal = sig.get('final_signal', 'HOLD')
        if signal != 'BUY':
            continue

        existing_mv = current_positions.get(code, {}).get('mv', Decimal('0'))
        name = TS_CODE_NAME.get(code, sig.get('name', code))
        desired = calc_desired_amount(sig, existing_mv)
        priority = calc_priority_score(sig)

        buy_signals.append({
            'ts_code': code,
            'name': name,
            'desired': desired,
            'priority': priority,
            'existing_mv': existing_mv,
        })

    # 按优先级排序 (高→低)
    buy_signals.sort(key=lambda x: x['priority'], reverse=True)

    # ----- 第三步：按优先级分配现金 -----
    # 可用买入资金 = 剩余现金 - 最低保留
    available_for_buys = remaining_cash - min_cash_reserve

    if available_for_buys > Decimal('0'):
        for bs in buy_signals:
            if available_for_buys <= Decimal('0'):
                # 现金耗尽, 剩余BUY信号全部跳过
                operations.append({
                    'ts_code': bs['ts_code'],
                    'name': bs['name'],
                    'action': '等待',  # 有信号但没钱
                    'value': Decimal('0'),
                    'priority': bs['priority'],
                    'reason': '现金不足, 优先级不足',
                })
                continue

            # 分配: 如果理想金额 > 可用现金, 按可用现金分配
            allocate = min(bs['desired'], available_for_buys)

            if allocate >= Decimal('1'):  # 至少1元才执行
                action_type = '建仓' if bs['existing_mv'] < Decimal('100') else '加仓'
                operations.append({
                    'ts_code': bs['ts_code'],
                    'name': bs['name'],
                    'action': action_type,
                    'value': allocate,
                    'priority': bs['priority'],
                })
                available_for_buys -= allocate
            else:
                operations.append({
                    'ts_code': bs['ts_code'],
                    'name': bs['name'],
                    'action': '等待',
                    'value': Decimal('0'),
                    'priority': bs['priority'],
                    'reason': '现金不足',
                })

    else:
        # 没有多余现金
        for bs in buy_signals:
            operations.append({
                'ts_code': bs['ts_code'],
                'name': bs['name'],
                'action': '等待',
                'value': Decimal('0'),
                'priority': bs['priority'],
                'reason': '现金不足',
            })

    # ----- 第四步：处理 HOLD 信号 (不动) -----
    for sig in signals_list:
        code = sig.get('ts_code', '')
        signal = sig.get('final_signal', 'HOLD')
        if signal != 'HOLD':
            continue
        operations.append({
            'ts_code': code,
            'name': TS_CODE_NAME.get(code, sig.get('name', code)),
            'action': '持有',
            'value': Decimal('0'),
            'priority': 0,
        })

    # 最终现金 = min_reserve + 未用完的买入资金
    cash_after = min_cash_reserve + available_for_buys
    return operations, cash_after


def format_plan_text(operations: List[Dict], cash_before: Decimal,
                     cash_after: Decimal, total_capital: Decimal) -> str:
    """生成投资计划文本"""
    lines = []
    lines.append("-" * 60)
    lines.append("[投资计划]")
    lines.append("-" * 60)
    lines.append(f"现金: RMB{cash_before:>8,.2f}  →  RMB{cash_after:>8,.2f}")
    lines.append("")

    buys = [op for op in operations if op['value'] > 0]
    sells = [op for op in operations if op['value'] < 0]
    waits = [op for op in operations if op['action'] == '等待']
    holds = [op for op in operations if op['action'] == '持有']

    if sells:
        lines.append(f"[卖出] (释放现金)")
        for op in sorted(sells, key=lambda x: x['value']):
            lines.append(f"  {op['name']:8s}  卖出 RMB{abs(op['value']):>7,.2f}")
        lines.append("")

    if buys:
        lines.append(f"[买入] (按优先级)")
        for i, op in enumerate(buys):
            lines.append(f"  #{i+1} {op['name']:8s}  买入 RMB{op['value']:>7,.2f}  "
                         f"(优先级: {op['priority']:.3f})")
        lines.append("")

    if waits:
        lines.append(f"[等待] (信号BUY但现金不足)")
        for op in waits:
            reason = op.get('reason', '')
            lines.append(f"  {op['name']:8s}  {reason}")
        lines.append("")

    if holds:
        lines.append(f"[持有] {len(holds)} 个指数维持不变")
        lines.append("")

    lines.append(f"最终现金: RMB{cash_after:>8,.2f}  "
                 f"仓位: {(float(total_capital) - float(cash_after)) / float(total_capital) * 100:.1f}%")
    lines.append("-" * 60)
    return '\n'.join(lines)
