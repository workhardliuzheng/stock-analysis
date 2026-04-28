"""
市场状态驱动的动态资产配置器

根据当前市场状态 (BULL_TREND / BEAR_TREND / SIDEWAYS 等)，
动态调整：
1. 目标权益/防御/现金比例
2. 各品种的买入/卖出优先级乘数
3. 整体风险敞口

核心逻辑:
- 牛市 → 重仓权益，积极做多
- 熊市 → 轻仓防御，现金为王
- 震荡 → 均衡配置，波段操作

关联模块:
- market_regime_detector.py → 提供市场状态
- investment_planner.py    → 按分配比例执行操作
- portfolio_tracker.py     → 跟踪持仓
"""

from decimal import Decimal
from typing import Dict, Tuple, List, Optional

# ============================================================
# 市场状态 → 目标配置
# ============================================================
# (权益仓位上限, 防御仓位下限, 最低现金比例)
# 权益 = 科创50/中证500/创业板指/深证成指等
# 防御 = 红利低波/国债ETF等低相关品种
# 现金 = 货币基金/国债逆回购/活期

REGIME_ALLOCATION = {
    'BULL_TREND': {   # 牛市: 积极做多
        'equity_max':  Decimal('0.80'),   # 权益上限 80%
        'defense_min': Decimal('0.05'),   # 防御下限 5%
        'cash_min':    Decimal('0.05'),   # 最低现金 5%
        'description': '牛市-积极',
    },
    'BULL_LATE': {    # 牛市末期: 逐步减仓
        'equity_max':  Decimal('0.65'),
        'defense_min': Decimal('0.15'),
        'cash_min':    Decimal('0.10'),
        'description': '牛市末期-谨慎',
    },
    'SIDEWAYS': {     # 震荡市: 均衡
        'equity_max':  Decimal('0.55'),
        'defense_min': Decimal('0.20'),
        'cash_min':    Decimal('0.15'),
        'description': '震荡-均衡',
    },
    'BEAR_LATE': {    # 熊市末期: 开始布局
        'equity_max':  Decimal('0.45'),
        'defense_min': Decimal('0.25'),
        'cash_min':    Decimal('0.20'),
        'description': '熊市末期-布局',
    },
    'BEAR_TREND': {   # 熊市: 防御为主
        'equity_max':  Decimal('0.25'),
        'defense_min': Decimal('0.30'),
        'cash_min':    Decimal('0.35'),
        'description': '熊市-防御',
    },
    'HIGH_VOL': {     # 高波动: 规避
        'equity_max':  Decimal('0.35'),
        'defense_min': Decimal('0.25'),
        'cash_min':    Decimal('0.30'),
        'description': '高波动-规避',
    },
}

# 默认状态（无数据时）
DEFAULT_ALLOC = REGIME_ALLOCATION['SIDEWAYS']

# ============================================================
# 品种分类
# ============================================================

# 权益类品种 (高波动，趋势跟踪)
EQUITY_CODES = [
    '000688.SH',  # 科创50
    '000905.SH',  # 中证500
    '399006.SZ',  # 创业板指
    '399001.SZ',  # 深证成指
    '000300.SH',  # 沪深300
    '000016.SH',  # 上证50
    '000852.SH',  # 中证1000
]

# 防御类品种 (低波动，均值回归)
DEFENSE_CODES = [
    # 后续加入:
    # '930955.CSI',  # 红利低波 (待加入)
    # '000092.SH',   # 上证国债 (待加入)
]


class RegimeAllocator:
    """
    市场状态驱动的资产配置器

    用法:
        allocator = RegimeAllocator()
        alloc = allocator.get_allocation('BEAR_TREND')
        # -> {'equity_max': 0.25, 'defense_min': 0.30, 'cash_min': 0.35, ...}

        mult = allocator.get_signal_multiplier('000688.SH', 'BUY', 'BEAR_TREND')
        # -> 0.3  (熊市买入科创板信号大幅弱化)
    """

    # 市场状态 → 信号乘数
    # 格式: {regime: {asset_type: {BUY_mult, SELL_mult, HOLD_mult}}}
    SIGNAL_MULTIPLIERS = {
        'BULL_TREND': {
            'equity':  {'BUY': Decimal('1.3'),  'SELL': Decimal('0.7'),  'HOLD': Decimal('1.0')},
            'defense': {'BUY': Decimal('0.8'),  'SELL': Decimal('1.0'),  'HOLD': Decimal('1.0')},
        },
        'BULL_LATE': {
            'equity':  {'BUY': Decimal('0.8'),  'SELL': Decimal('1.2'),  'HOLD': Decimal('1.0')},
            'defense': {'BUY': Decimal('1.0'),  'SELL': Decimal('0.8'),  'HOLD': Decimal('1.0')},
        },
        'SIDEWAYS': {
            'equity':  {'BUY': Decimal('1.0'),  'SELL': Decimal('1.0'),  'HOLD': Decimal('1.0')},
            'defense': {'BUY': Decimal('1.0'),  'SELL': Decimal('1.0'),  'HOLD': Decimal('1.0')},
        },
        'BEAR_LATE': {
            'equity':  {'BUY': Decimal('0.7'),  'SELL': Decimal('1.3'),  'HOLD': Decimal('1.0')},
            'defense': {'BUY': Decimal('1.2'),  'SELL': Decimal('0.6'),  'HOLD': Decimal('1.0')},
        },
        'BEAR_TREND': {
            'equity':  {'BUY': Decimal('0.2'),  'SELL': Decimal('1.8'),  'HOLD': Decimal('1.0')},
            'defense': {'BUY': Decimal('1.3'),  'SELL': Decimal('0.4'),  'HOLD': Decimal('1.0')},
        },
        'HIGH_VOL': {
            'equity':  {'BUY': Decimal('0.4'),  'SELL': Decimal('1.5'),  'HOLD': Decimal('1.0')},
            'defense': {'BUY': Decimal('1.1'),  'SELL': Decimal('0.7'),  'HOLD': Decimal('1.0')},
        },
    }

    def __init__(self, regime: str = None):
        """
        Args:
            regime: 当前市场状态，None 则默认 SIDEWAYS
        """
        self.regime = regime or 'SIDEWAYS'

    def set_regime(self, regime: str):
        """更新市场状态"""
        self.regime = regime

    def get_allocation(self, regime: str = None) -> Dict:
        """
        获取当前市场状态的目标配置比例

        Returns:
            {
                'equity_max': Decimal(0.80),  # 权益仓位上限
                'defense_min': Decimal(0.05),  # 防御仓位下限
                'cash_min': Decimal(0.05),     # 最低现金比例
                'description': '牛市-积极',
            }
        """
        r = regime or self.regime
        return REGIME_ALLOCATION.get(r, DEFAULT_ALLOC)

    def classify_code(self, ts_code: str) -> str:
        """分类品种: 'equity' 或 'defense'"""
        if ts_code in DEFENSE_CODES:
            return 'defense'
        return 'equity'

    def get_signal_multiplier(self, ts_code: str, signal: str,
                              regime: str = None) -> Decimal:
        """
        获取信号乘数 (用于调整投资计划器的优先级)

        Args:
            ts_code: 指数代码
            signal: BUY / SELL / HOLD
            regime: 市场状态

        Returns:
            Decimal: 乘数 (0.2~1.8)
        """
        r = regime or self.regime
        asset_type = self.classify_code(ts_code)

        regime_mults = self.SIGNAL_MULTIPLIERS.get(r, self.SIGNAL_MULTIPLIERS['SIDEWAYS'])
        type_mults = regime_mults.get(asset_type, regime_mults.get('equity', {}))
        return type_mults.get(signal, Decimal('1.0'))

    def adjust_signal(self, signal_dict: Dict) -> Dict:
        """
        根据市场状态调整信号

        在熊市中:
        - 权益类 BUY → 降低优先级 (乘数0.2)
        - 权益类 SELL → 提高优先级 (乘数1.8)
        - 防御类 BUY → 提高优先级 (乘数1.3)
        - 防御类 SELL → 降低优先级 (乘数0.4)

        Args:
            signal_dict: 原始信号字典

        Returns:
            调整后的信号字典 (修改 final_confidence)
        """
        code = signal_dict.get('ts_code', '')
        signal = signal_dict.get('final_signal', 'HOLD')
        multiplier = self.get_signal_multiplier(code, signal)

        # 调整置信度 (信心的强弱影响操作金额)
        original_conf = Decimal(str(signal_dict.get('final_confidence', 0.5)))
        adjusted_conf = (original_conf * multiplier).quantize(Decimal('0.01'))
        adjusted_conf = min(adjusted_conf, Decimal('1.0'))  # 不超过1
        adjusted_conf = max(adjusted_conf, Decimal('0.01'))  # 不低于0.01

        result = dict(signal_dict)
        result['final_confidence'] = float(adjusted_conf)
        result['_regime_multiplier'] = float(multiplier)
        result['_regime'] = self.regime
        return result

    def summary_text(self, regime: str = None) -> str:
        """生成配置概览文本"""
        r = regime or self.regime
        alloc = self.get_allocation(r)
        lines = []
        lines.append("-" * 60)
        lines.append(f"[宏观配置] 市场状态: {r} ({alloc['description']})")
        lines.append("-" * 60)
        lines.append(f"  权益上限: {float(alloc['equity_max'])*100:.0f}%")
        lines.append(f"  防御下限: {float(alloc['defense_min'])*100:.0f}%")
        lines.append(f"  最低现金: {float(alloc['cash_min'])*100:.0f}%")
        lines.append("")
        lines.append("  信号调整:")
        lines.append(f"  权益 BUY:  ×{float(self.get_signal_multiplier('000688.SH','BUY',r)):.1f}")
        lines.append(f"  权益 SELL: ×{float(self.get_signal_multiplier('000688.SH','SELL',r)):.1f}")
        lines.append(f"  防御 BUY:  ×{float(self.get_signal_multiplier('000092.SH','BUY',r)):.1f}")
        lines.append(f"  防御 SELL: ×{float(self.get_signal_multiplier('000092.SH','SELL',r)):.1f}")
        return '\n'.join(lines)


def estimate_market_regime(signals_list: List[Dict]) -> str:
    """
    从信号列表中估算综合市场状态

    用所有指数的 trend_state 投票决定整体市场状态:
    - rising > 50% → BULL_TREND
    - falling > 50% → BEAR_TREND
    - 其他 → SIDEWAYS

    Args:
        signals_list: 信号列表

    Returns:
        regime: BULL_TREND / BEAR_TREND / SIDEWAYS
    """
    if not signals_list:
        return 'SIDEWAYS'

    rising = sum(1 for s in signals_list if s.get('trend_state') == 'rising')
    falling = sum(1 for s in signals_list if s.get('trend_state') == 'falling')
    total = len(signals_list)

    if total == 0:
        return 'SIDEWAYS'

    if rising / total >= 0.5:
        return 'BULL_TREND'
    elif falling / total >= 0.5:
        return 'BEAR_TREND'
    else:
        return 'SIDEWAYS'
