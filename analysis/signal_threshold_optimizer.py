"""
V7-4 信号阈值优化模块

修改MultiFactorScorer的信号生成逻辑，增加信号频率
"""

from typing import Dict, Tuple
import numpy as np


class SignalThresholdOptimizer:
    """
    信号阈值优化器
    
    功能:
    1. 调整BUY/SELL信号生成阈值
    2. 支持多种阈值策略
    3. 动态阈值调整
    
    策略选择:
    - strategy='default': 默认阈值 (保守)
    - strategy='aggressive': 激进阈值 (增加信号)
    - strategy='dynamic': 动态阈值 (根据波动率调整)
    - strategy='hybrid': 混合策略 (阈值+变化率)
    """
    
    # 策略配置
    STRATEGIES = {
        'default': {
            'uptrend': {'buy': 60, 'sell': 40},
            'downtrend': {'buy': 70, 'sell': 30},
            'sideways': {'buy': 65, 'sell': 35},
        },
        'aggressive': {
            'uptrend': {'buy': 55, 'sell': 45},
            'downtrend': {'buy': 55, 'sell': 45},
            'sideways': {'buy': 55, 'sell': 45},
        },
        'aggressive_lite': {
            'uptrend': {'buy': 52, 'sell': 48},
            'downtrend': {'buy': 52, 'sell': 48},
            'sideways': {'buy': 52, 'sell': 48},
        },
        'dynamic': {
            # 根据波动率调整
            'low_volatility': {
                'uptrend': {'buy': 58, 'sell': 42},
                'downtrend': {'buy': 58, 'sell': 42},
                'sideways': {'buy': 58, 'sell': 42},
            },
            'high_volatility': {
                'uptrend': {'buy': 50, 'sell': 50},
                'downtrend': {'buy': 50, 'sell': 50},
                'sideways': {'buy': 50, 'sell': 50},
            }
        },
        'hybrid': {
            # 结合评分变化率
            'threshold': {'buy': 55, 'sell': 45},
            'delta_threshold': 5.0,  # 评分变化率阈值
        }
    }
    
    def __init__(self, strategy: str = 'aggressive_lite'):
        """
        Args:
            strategy: 信号阈值策略
        """
        self.strategy = strategy
        self.config = self.STRATEGIES.get(strategy, self.STRATEGIES['aggressive_lite'])
        
        print(f"[OK] V7-4 信号阈值优化器初始化")
        print(f"[OK] 当前策略: {strategy}")
        print(f"[OK] 配置: {self.config}")
    
    def get_thresholds(self, trend_state: str, volatility: float = 1.5) -> Dict[str, float]:
        """
        获取信号阈值
        
        Args:
            trend_state: 趋势状态 (uptrend/downtrend/sideways)
            volatility: 波动率 (用于dynamic策略)
        
        Returns:
            Dict[str, float]: {'buy': x, 'sell': y}
        """
        if self.strategy == 'dynamic':
            if volatility > 2.0:
                return self.config['high_volatility'][trend_state]
            else:
                return self.config['low_volatility'][trend_state]
        else:
            return self.config[trend_state]
    
    def generate_signal(self, score: float, trend_state: str, 
                       score_delta: float = 0.0, score_delta_ratio: float = 0.0,
                       volatility: float = 1.5) -> Tuple[str, float]:
        """
        生成信号
        
        Args:
            score: 多因子综合评分 (0-100)
            trend_state: 趋势状态 (uptrend/downtrend/sideways)
            score_delta: 评分变化量 (用于hybrid策略)
            score_delta_ratio: 评分变化率 (用于hybrid策略)
            volatility: 波动率 (用于dynamic策略)
        
        Returns:
            Tuple[str, float]: (signal, confidence)
        """
        # 获取阈值
        thresholds = self.get_thresholds(trend_state, volatility)
        
        # 应用评分变化率
        if self.strategy == 'hybrid' and abs(score_delta_ratio) > self.config['delta_threshold']:
            # 评分快速上升/下降，降低阈值
            buy_threshold = min(thresholds['buy'], 55)
            sell_threshold = max(thresholds['sell'], 45)
        else:
            buy_threshold = thresholds['buy']
            sell_threshold = thresholds['sell']
        
        # 生成信号
        if score >= buy_threshold:
            signal = 'BUY'
            confidence = (score - 50) / 50.0
        elif score <= sell_threshold:
            signal = 'SELL'
            confidence = (50 - score) / 50.0
        else:
            signal = 'HOLD'
            confidence = 0.5
        
        # 限制信心度范围
        confidence = max(0.0, min(1.0, confidence))
        
        return signal, round(confidence, 2)


# 预定义策略工厂
def get_default_threshold_optimizer() -> SignalThresholdOptimizer:
    """默认优化策略 (保守)"""
    return SignalThresholdOptimizer(strategy='default')


def get_aggressive_threshold_optimizer() -> SignalThresholdOptimizer:
    """激进优化策略 (增加信号)"""
    return SignalThresholdOptimizer(strategy='aggressive')


def get_aggressive_lite_threshold_optimizer() -> SignalThresholdOptimizer:
    """轻度激进优化策略 (适度增加信号)"""
    return SignalThresholdOptimizer(strategy='aggressive_lite')


def get_dynamic_threshold_optimizer() -> SignalThresholdOptimizer:
    """动态阈值优化策略 (根据波动率调整)"""
    return SignalThresholdOptimizer(strategy='dynamic')


def get_hybrid_threshold_optimizer() -> SignalThresholdOptimizer:
    """混合策略 (阈值+变化率)"""
    return SignalThresholdOptimizer(strategy='hybrid')
