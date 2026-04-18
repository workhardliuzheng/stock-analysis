"""
V12.1 上证50/上证综指专项优化模块

解决V11版本中上证50/上证综指负贡献问题：
- 上证50 BUY/SELL比0.47仍偏SELL
- 上证综指和中证500有负贡献
- SIDEWAYS占比>60%的指数共识阈值需要调整

优化方案：
1. 调整V11的CONSENSUS_THRESHOLDS，针对大盘股指数调整震荡市阈值
2. 增加大盘股专属特征（沪深300驱动因子）
3. 优化大盘股regime参数配置
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple


# V11原始共识投票阈值
ORIGINAL_CONSENSUS_THRESHOLDS = {
    'BULL_TREND': {'bull_thresh': 3, 'bear_thresh': -3},
    'BULL_LATE':  {'bull_thresh': 4, 'bear_thresh': -2},
    'BEAR_TREND': {'bull_thresh': 4, 'bear_thresh': -2},
    'BEAR_LATE':  {'bull_thresh': 3, 'bear_thresh': -3},
    'SIDEWAYS':   {'bull_thresh': 4, 'bear_thresh': -3},
    'HIGH_VOL':   {'bull_thresh': 4, 'bear_thresh': -3},
}

# V12.1优化后的共识投票阈值（针对大盘股优化）
OPTIMIZED_CONSENSUS_THRESHOLDS_V121 = {
    'BULL_TREND': {'bull_thresh': 3, 'bear_thresh': -3},      # 牛市趋势不变
    'BULL_LATE':  {'bull_thresh': 3, 'bear_thresh': -2},      # 牛市末期：降低看涨阈值(4->3)
    'BEAR_TREND': {'bull_thresh': 4, 'bear_thresh': -2},      # 熊市趋势：降低看跌阈值(-3->-2)
    'BEAR_LATE':  {'bull_thresh': 3, 'bear_thresh': -3},      # 熊市末期不变
    'SIDEWAYS':   {'bull_thresh': 3, 'bear_thresh': -2},      # 震荡市：显著降低看涨阈值(4->3)，降低看跌阈值(-3->-2)
    'HIGH_VOL':   {'bull_thresh': 3, 'bear_thresh': -2},      # 高波动：降低看涨阈值(4->3)，降低看跌阈值(-3->-2)
}

# 大盘股专用阈值（针对上证50/上证综指/沪深300）
LARGE_CAP_CONSENSUS_THRESHOLDS = {
    'BULL_TREND': {'bull_thresh': 3, 'bear_thresh': -3},
    'BULL_LATE':  {'bull_thresh': 3, 'bear_thresh': -2},
    'BEAR_TREND': {'bull_thresh': 4, 'bear_thresh': -2},
    'BEAR_LATE':  {'bull_thresh': 3, 'bear_thresh': -3},
    'SIDEWAYS':   {'bull_thresh': 3, 'bear_thresh': -2},  # 震荡市更积极
    'HIGH_VOL':   {'bull_thresh': 3, 'bear_thresh': -2},  # 高波动更积极
}

# 各状态对应的多因子权重（V11版本）
FACTOR_WEIGHTS_BY_REGIME = {
    'BULL_TREND': {'trend': 0.40, 'momentum': 0.30, 'volume': 0.10, 'valuation': 0.10, 'volatility': 0.10},
    'BULL_LATE':  {'trend': 0.20, 'momentum': 0.15, 'volume': 0.15, 'valuation': 0.30, 'volatility': 0.20},
    'BEAR_TREND': {'trend': 0.25, 'momentum': 0.15, 'volume': 0.20, 'valuation': 0.25, 'volatility': 0.15},
    'BEAR_LATE':  {'trend': 0.25, 'momentum': 0.20, 'volume': 0.15, 'valuation': 0.30, 'volatility': 0.10},
    'SIDEWAYS':   {'trend': 0.25, 'momentum': 0.25, 'volume': 0.20, 'valuation': 0.20, 'volatility': 0.10},
    'HIGH_VOL':   {'trend': 0.20, 'momentum': 0.15, 'volume': 0.15, 'valuation': 0.20, 'volatility': 0.30},
}

# V12.1优化后的多因子权重（增加大盘股特征权重）
OPTIMIZED_FACTOR_WEIGHTS_V121 = {
    'BULL_TREND': {'trend': 0.45, 'momentum': 0.30, 'volume': 0.10, 'valuation': 0.10, 'volatility': 0.05},
    'BULL_LATE':  {'trend': 0.25, 'momentum': 0.15, 'volume': 0.15, 'valuation': 0.35, 'volatility': 0.10},
    'BEAR_TREND': {'trend': 0.30, 'momentum': 0.15, 'volume': 0.20, 'valuation': 0.25, 'volatility': 0.10},
    'BEAR_LATE':  {'trend': 0.30, 'momentum': 0.20, 'volume': 0.15, 'valuation': 0.25, 'volatility': 0.10},
    'SIDEWAYS':   {'trend': 0.30, 'momentum': 0.20, 'volume': 0.20, 'valuation': 0.20, 'volatility': 0.10},
    'HIGH_VOL':   {'trend': 0.25, 'momentum': 0.15, 'volume': 0.15, 'valuation': 0.20, 'volatility': 0.25},
}


class MarketRegimeOptimizerV121:
    """
    V12.1 市场状态优化器
    
    解决上证50/上证综指负贡献问题：
    1. 调整共识投票阈值（震荡市更积极）
    2. 增加大盘股专属特征（沪深300驱动因子）
    3. 优化大盘股regime参数配置
    """
    
    def __init__(self,
                 large_cap_indices: List[str] = None,
                 use_optimized_thresholds: bool = True,
                 use_optimized_weights: bool = True):
        """
        Args:
            large_cap_indices: 大盘股指数列表 (默认: ['000016.SH', '000001.SH', '000300.SH'])
            use_optimized_thresholds: 是否使用优化后的共识阈值
            use_optimized_weights: 是否使用优化后的因子权重
        """
        self.large_cap_indices = large_cap_indices or ['000016.SH', '000001.SH', '000300.SH']
        self.use_optimized_thresholds = use_optimized_thresholds
        self.use_optimized_weights = use_optimized_weights
        
        print(f"[OK] V12.1 MarketRegimeOptimizer 初始化")
        print(f"  大盘股指数: {self.large_cap_indices}")
        print(f"  优化共识阈值: {use_optimized_thresholds}")
        print(f"  优化因子权重: {use_optimized_weights}")
    
    def get_consen<TRUNCATED>>>
The output created 1 file but does not have executable permission. Running chmod +x.