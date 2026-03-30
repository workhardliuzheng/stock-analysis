"""
仓位管理模块

提供多种仓位分配策略，支持多指数分散持仓、风险控制和空仓逻辑。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PositionConfig:
    """仓位配置参数"""
    max_position_per_index: float = 0.30  # 单指数最大仓位 30%
    max_total_position: float = 0.90       # 总仓位上限 90%
    min_confidence_threshold: float = 0.0  # 最小信号强度阈值
    risk_free_rate: float = 0.02 / 252     # 日无风险利率 (2%年化)


class PositionManager:
    """
    仓位管理器
    
    功能:
    1. 多指数分散持仓
    2. 动态仓位分配
    3. 风险控制
    4. 空仓条件判断
    """
    
    def __init__(self, config: PositionConfig = None):
        """
        Args:
            config: 仓位配置参数
        """
        self.config = config or PositionConfig()
    
    def calculate_positions(self, 
                           index_signals: Dict[str, dict],
                           cash_available: float = 1.0) -> Dict[str, float]:
        """
        计算各指数的持仓比例
        
        Args:
            index_signals: 各指数的信号字典
                {
                    '000300.SH': {
                        'signal': 'BUY/SELL/HOLD',
                        'confidence': 0.65,
                        'predicted_return': 0.01,  # 预测收益率
                        'volatility': 0.02         # 波动率
                    },
                    ...
                }
            cash_available: 可用资金比例
        
        Returns:
            Dict[str, float]: 各指数的仓位比例
                {'000300.SH': 0.25, '399006.SZ': 0.15, ...}
        """
        # 过滤出有效信号（信号强度 > 0）
        valid_signals = {
            code: data for code, data in index_signals.items()
            if data.get('signal') in ['BUY', 'SELL'] 
            and data.get('confidence', 0) > 0
        }
        
        if not valid_signals:
            # 没有有效信号，空仓
            return {}
        
        # 计算各指数的评分（用于仓位分配）
        scores = self._calculate_scores(valid_signals)
        
        # 根据评分分配仓位
        positions = self._allocate_positions(scores, cash_available)
        
        return positions
    
    def _calculate_scores(self, signals: Dict[str, dict]) -> Dict[str, float]:
        """
        计算各指数的仓位评分
        
        评分考虑因素:
        1. 预测收益率 (权重50%)
        2. 信号强度/ confidence (权重30%)
        3. 风险调整后收益 (权重20%)
        
        Returns:
            Dict[str, float]: 各指数的评分
        """
        scores = {}
        
        # 提取各项指标
        predicted_returns = {k: v.get('predicted_return', 0) for k, v in signals.items()}
        confidences = {k: v.get('confidence', 0) for k, v in signals.items()}
        volatilities = {k: v.get('volatility', 0.02) for k, v in signals.items()}
        
        # 归一化
        if predicted_returns:
            max_return = max(predicted_returns.values())
            min_return = min(predicted_returns.values())
            range_return = max_return - min_return if max_return != min_return else 1.0
            norm_returns = {
                k: (v - min_return) / range_return if range_return > 0 else 0.5
                for k, v in predicted_returns.items()
            }
            # 负收益归一化为0
            norm_returns = {k: max(0, v) for k, v in norm_returns.items()}
        else:
            norm_returns = {k: 0.5 for k in signals.keys()}
        
        if confidences:
            max_conf = max(confidences.values())
            min_conf = min(confidences.values())
            range_conf = max_conf - min_conf if max_conf != min_conf else 1.0
            norm_confidences = {
                k: (v - min_conf) / range_conf if range_conf > 0 else 0.5
                for k, v in confidences.items()
            }
        else:
            norm_confidences = {k: 0.5 for k in signals.keys()}
        
        if volatilities:
            max_vol = max(volatilities.values())
            min_vol = min(volatilities.values())
            range_vol = max_vol - min_vol if max_vol != min_vol else 0.02
            norm_volatilities = {
                k: (max_vol - (v - min_vol)) / range_vol if range_vol > 0 else 0.5
                for k, v in volatilities.items()
            }
        else:
            norm_volatilities = {k: 0.5 for k in signals.keys()}
        
        # 综合评分 (添加小常数避免全0)
        for code in signals.keys():
            score = (
                norm_returns.get(code, 0.5) * 0.5 +
                norm_confidences.get(code, 0.5) * 0.3 +
                norm_volatilities.get(code, 0.5) * 0.2
            )
            scores[code] = max(0.01, score)  # 至少有个基础分
        
        return scores
    
    def _allocate_positions(self, 
                           scores: Dict[str, float], 
                           cash_available: float = 1.0) -> Dict[str, float]:
        """
        根据评分分配仓位
        
        Args:
            scores: 各指数评分
            cash_available: 可用资金比例 (0-1)
        
        Returns:
            Dict[str, float]: 仓位分配
        """
        if not scores:
            return {}
        
        # 计算总分
        total_score = sum(scores.values())
        
        # 初步分配 (未考虑上限)
        raw_positions = {
            code: (score / total_score) * cash_available
            for code, score in scores.items()
        }
        
        # 施加约束
        positions = {}
        total_position = 0.0
        
        # 获取上限参数（兼容 PositionConfig 和 AdvancedPositionConfig）
        max_pos_per_index = getattr(self.config, 'max_position_per_index', 0.30)
        max_total_pos = getattr(self.config, 'max_total_position', 0.90)
        
        for code, raw_pos in raw_positions.items():
            # 单指数上限
            limited_pos = min(raw_pos, max_pos_per_index)
            positions[code] = limited_pos
            total_position += limited_pos
        
        # 总仓位上限
        if total_position > max_total_pos:
            scale_factor = max_total_pos / total_position
            positions = {code: pos * scale_factor for code, pos in positions.items()}
        
        # 清理小仓位
        positions = {code: round(pos, 4) for code, pos in positions.items() if pos >= 0.01}
        
        return positions
    
    def should_empty_position(self, index_signals: Dict[str, dict]) -> bool:
        """
        判断是否应该空仓
        
        条件:
        1. 所有指数预测收益都为负
        2. 或者所有信号强度都很低
        
        Args:
            index_signals: 各指数信号
        
        Returns:
            bool: 是否空仓
        """
        if not index_signals:
            return True
        
        # 检查是否有正收益的指数
        has_positive_prediction = any(
            data.get('predicted_return', 0) > 0 
            for data in index_signals.values()
        )
        
        # 检查是否有有效信号
        has_buy_signal = any(
            data.get('signal') == 'BUY' 
            for data in index_signals.values()
        )
        
        # 至少满足一个条件才不空仓
        return not (has_positive_prediction or has_buy_signal)
    
    # ==================== 多信号组合 ====================
    
    def calculate_positions_with_threshold(self,
                                          index_signals: Dict[str, dict],
                                          min_predicted_return: float = 0.0,
                                          min_confidence: float = 0.5) -> Dict[str, float]:
        """
        带阈值过滤的仓位计算
        
        Args:
            index_signals: 各指数信号
            min_predicted_return: 最小预测收益率阈值
            min_confidence: 最小信号强度阈值
        
        Returns:
            Dict[str, float]: 仓位分配
        """
        # 过滤信号
        filtered = {
            code: data for code, data in index_signals.items()
            if data.get('predicted_return', 0) > min_predicted_return
            and data.get('confidence', 0) > min_confidence
        }
        
        return self.calculate_positions(filtered)
    
    def calculate_risk_adjusted_positions(self,
                                         index_signals: Dict[str, dict],
                                         risk_aversion: float = 1.0) -> Dict[str, float]:
        """
        风险调整后的仓位计算 (均值-方差优化简化版)
        
        评分 = 预测收益 - 0.5 * 风险厌恶系数 * 波动率^2
        
        Args:
            index_signals: 各指数信号
            risk_aversion: 风险厌恶系数 (越大越保守)
        
        Returns:
            Dict[str, float]: 仓位分配
        """
        scores = {}
        
        for code, data in index_signals.items():
            predicted_return = data.get('predicted_return', 0)
            volatility = data.get('volatility', 0.02)
            
            # 风险调整后收益 (使用年化波动率)
            # 假设 volatility 是日波动率，年化 = volatility * sqrt(252)
            annualized_vol = volatility * 3.0  # 简化：约等于年化波动率
            adjusted_return = predicted_return - 0.5 * risk_aversion * (annualized_vol ** 2)
            
            if adjusted_return > 0:
                scores[code] = max(adjusted_return, 0.001)  # 至少0.1%
        
        # 如果所有指数风险调整后收益都为负，建议空仓
        if not scores:
            return {}
        
        return self._allocate_positions(scores)


# ==================== 仓位回测器 ====================

class PositionBacktester:
    """
    仓位管理回测器
    
    支持多指数分散持仓的回测，计算组合收益率。
    """
    
    def __init__(self, 
                 initial_capital: float = 100000,
                 commission_rate: float = 0.00006,
                 position_manager: PositionManager = None):
        """
        Args:
            initial_capital: 初始资金
            commission_rate: 单边佣金率
            position_manager: 仓位管理器
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.position_manager = position_manager or PositionManager()
    
    def run(self, 
            df_list: List[pd.DataFrame],
            signal_columns: List[str],
            position_data: List[Dict[str, dict]]) -> dict:
        """
        运行仓位管理回测
        
        Args:
            df_list: 各指数的DataFrame列表
            signal_columns: 各指数的信号列名列表
            position_data: 每日的仓位配置数据列表
        
        Returns:
            dict: 回测结果
        """
        # TODO: 实现多指数回测逻辑
        pass
