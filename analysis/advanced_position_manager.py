"""
高级仓位管理器

功能:
- 差异化阈值：不同指数使用不同阈值（大盘0.05%，小盘0.03%，科创50/中证1000更激进）
- 止损机制：单指数-5%止损，组合-15%紧急空仓
- 仓位动态调整：根据市场状态调整仓位权重

作者: Zeno
日期: 2026-03-30
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class AdvancedPositionConfig:
    """高级仓位配置"""
    # 差异化阈值配置
    index_thresholds: Dict[str, float] = None  # 指数代码 -> 阈值
    default_threshold: float = 0.05  # 默认阈值
    
    # 止损配置
    stop_loss_single: float = -0.05  # 单指数止损阈值 (-5%)
    stop_loss_portfolio: float = -0.15  # 组合止损阈值 (-15%)
    
    # 仓位权重配置
    peak_scaler: float = 0.3  # 历史峰值权重（越高越保守）
    market_regime_weight: float = 0.2  # 市场状态权重
    
    # 市场状态识别
    market_above_ma200: bool = True  # 是否高于MA200（用于仓位调整）
    
    def __post_init__(self):
        if self.index_thresholds is None:
            # 默认配置：大盘较低，小盘更高
            self.index_thresholds = {
                '000300.SH': 0.05,   # 沪深300 - 大盘
                '000016.SH': 0.05,   # 上证50 - 大盘
                '000001.SH': 0.06,   # 上证综指 - 中等
                '399001.SZ': 0.07,   # 深证成指 - 中等
                '399006.SZ': 0.08,   # 创业板指 - 中小盘
                '000688.SH': 0.10,   # 科创50 - 小盘
                '000852.SH': 0.12,   # 中证1000 - 小盘
                '000905.SH': 0.10,   # 中证500 - 中小盘
            }


class AdvancedPositionManager:
    """
    高级仓位管理器
    
    功能:
    1. 差异化阈值：根据指数类型调整阈值
    2. 止损机制：单指数最高回撤5%，组合最高回撤15%
    3. 仓位动态调整：根据市场状态调整仓位权重
    
    仓位计算公式:
    ```
    base_position = predicted_return * scalable_weight
    peak_adjustment = base_position * peak_scaler * (1 - peak_ratio)
    market_adjustment = base_position * market_regime_weight * market_factor
    
    final_position = base_position + peak_adjustment + market_adjustment
    final_position = min(max(final_position, 0), max_position)
    ```
    """
    
    MAX_POSITION = 0.30  # 单指数最大仓位 (30%)
    
    def __init__(self, config: AdvancedPositionConfig = None):
        self.config = config or AdvancedPositionConfig()
        self.positions: Dict[str, float] = {}  # 当前仓位
        self.holdings: Dict[str, float] = {}  # 当前持股数
        self.entries: Dict[str, float] = {}  # 入场价格
        self.max_prices: Dict[str, float] = {}  # 历史最高价格
        self.portfolio_max_value: float = 0.0  # 组合历史最高价值
        
    def reset(self):
        """重置所有状态"""
        self.positions = {}
        self.holdings = {}
        self.entries = {}
        self.max_prices = {}
        self.portfolio_max_value = 0.0
        
    def calculate_positions(self, 
                          index_signals: Dict[str, dict],
                          cash_available: float = 1.0,
                          current_prices: Dict[str, float] = None,
                          portfolio_value: float = 100000.0) -> Dict[str, float]:
        """
        计算仓位分配
        
        Args:
            index_signals: 各指数的信号字典 (兼容 PositionManager)
            cash_available: 可用资金比例
            current_prices: 当前价格
            portfolio_value: 组合当前价值
            
        Returns:
            Dict[str, float]: 各指数的目标仓位比例
        """
        if current_prices is None:
            current_prices = {}
            
        # 1. 检查止损条件
        if self._check_stop_loss(index_signals, portfolio_value):
            print(f"  [止损触发] 组合回撤超过 {self.config.stop_loss_portfolio*100:.1f}%，全部清仓")
            return {code: 0.0 for code in index_signals}
        
        # 2. 计算基础仓位
        target_positions = {}
        for code, signal in index_signals.items():
            # 检查单指数止损
            if self._check_single_stop_loss(code, signal, current_prices.get(code, 0)):
                target_positions[code] = 0.0
                continue
                
            # 计算仓位
            position = self._calculate_position(code, signal, cash_available)
            target_positions[code] = position
            
        # 3. 调整总仓位（市场择时）
        total_position = sum(target_positions.values())
        market_factor = self._get_market_factor(index_signals)
        adjusted_total = total_position * market_factor
        
        # 按比例缩放
        if adjusted_total > 0:
            scale = min(adjusted_total / total_position, 1.0)
            for code in target_positions:
                target_positions[code] *= scale
        
        # 4. 更新状态
        self._update_status(target_positions, current_prices, portfolio_value)
        
        return target_positions
    
    def _calculate_position(self, code: str, signal: dict, cash_available: float) -> float:
        """
        计算单指数仓位
        
        差异化阈值逻辑:
        - 大盘指数 (沪深300/上证50): 阈值 0.05%
        - 中等指数 (上证综指/深证成指): 阈值 0.06-0.07%
        - 小盘指数 (科创50/中证1000): 阈值 0.08-0.12%
        
        仓位公式:
        position = predicted_return * scalable_weight * index_multiplier
        """
        predicted_return = signal.get('predicted_return', 0)
        confidence = signal.get('confidence', 0.5)
        
        # 获取指数特定阈值
        threshold = self.config.index_thresholds.get(code, self.config.default_threshold)
        
        # 计算指数乘数（越小盘，乘数越大）
        index_multiplier = threshold / self.config.default_threshold
        
        # 基础仓位（带置信度）
        base_position = predicted_return * 0.8 * confidence
        
        # 应用指数乘数
        adjusted_position = base_position * index_multiplier
        
        # 添加峰值调整（保守）
        if code in self.max_prices and self.max_prices[code] > 0:
            peak_ratio = self.max_prices[code] / max(1, adjusted_position * 100)
            peak_factor = 1.0 - self.config.peak_scaler * (1 - 1/peak_ratio)
            adjusted_position *= peak_factor
        
        # 应用市场状态调整
        market_factor = self.config.market_above_ma200 * 1.0 + (1 - self.config.market_above_ma200) * 0.7
        adjusted_position *= market_factor
        
        # 限制范围
        position = max(0.0, min(adjusted_position, self.MAX_POSITION))
        
        # 信号强度调整
        signal_type = signal.get('signal', 'HOLD')
        if signal_type == 'HOLD':
            position *= 0.5
        elif signal_type == 'SELL':
            position = 0.0
            
        return position
    
    def _check_stop_loss(self, signals: dict, portfolio_value: float) -> bool:
        """
        检查组合止损
        
        要求: 组合总回撤超过 -15% 时触发止损，全部清仓
        """
        if self.portfolio_max_value <= 0:
            return False
            
        drawdown = (portfolio_value - self.portfolio_max_value) / self.portfolio_max_value
        return drawdown <= self.config.stop_loss_portfolio
    
    def _check_single_stop_loss(self, code: str, signal: dict, current_price: float) -> bool:
        """
        检查单指数止损
        
        要求: 单指数回撤超过 -5% 时触发止损，清仓该指数
        """
        if code not in self.entries or self.entries[code] <= 0:
            return False
            
        if code not in self.max_prices or self.max_prices[code] <= 0:
            return False
            
        # 计算当前回撤
        current_drawdown = (current_price - self.entries[code]) / self.entries[code]
        max_drawdown = (self.max_prices[code] - current_price) / self.max_prices[code]
        
        # 检查止损条件
        if max_drawdown >= -self.config.stop_loss_single:
            print(f"  [止损触发] {code} 回撤 {max_drawdown*100:.1f}% 超过 {-self.config.stop_loss_single*100:.1f}%")
            return True
            
        return False
    
    def _get_market_factor(self, signals: dict) -> float:
        """
        获取市场状态因子
        
        逻辑:
        - 沪深300 > MA200: factor = 1.0 (正常)
        - 沪深300 <= MA200: factor = 0.7 (偏谨慎)
        """
        if '000300.SH' in signals:
            signal = signals['000300.SH']
            # 读取 market_timing 信号
            market_timing = signal.get('market_timing', 1)
            return market_timing
        return 1.0
    
    def _update_status(self, target_positions: dict, current_prices: dict, portfolio_value: float):
        """更新内部状态"""
        self.positions = target_positions
        
        # 更新组合历史最高值
        if portfolio_value > self.portfolio_max_value:
            self.portfolio_max_value = portfolio_value
            
        # 更新持仓价格
        for code, price in current_prices.items():
            if code in target_positions:
                if code not in self.entries or self.entries[code] == 0:
                    self.entries[code] = price
                if price > self.max_prices.get(code, 0):
                    self.max_prices[code] = price
                if code in target_positions and target_positions[code] > 0:
                    self.entries[code] = price
                    self.max_prices[code] = price
                elif code in target_positions and target_positions[code] == 0:
                    self.entries[code] = 0
                    self.max_prices[code] = 0
    
    def set_market_timing(self, above_ma200: bool):
        """设置市场择时状态"""
        self.config.market_above_ma200 = above_ma200
    
    def get_recommended_threshold(self, code: str) -> float:
        """获取指数建议阈值"""
        return self.config.index_thresholds.get(code, self.config.default_threshold)
    
    def calculate_positions_v6(self,
                             signals: Dict[str, dict],
                             cash_available: float = 1.0,
                             portfolio_value: float = 100000.0,
                             current_prices: Dict[str, float] = None) -> Dict[str, float]:
        """
        V6版本仓位计算（支持止损和动态调仓）
        
        Args:
            signals: 各指数的信号字典
            cash_available: 可用资金比例
            portfolio_value: 组合当前价值
            current_prices: 当前价格
            
        Returns:
            Dict[str, float]: 各指数的目标仓位比例
        """
        return self.calculate_positions(
            index_signals=signals,  # 修正参数名
            cash_available=cash_available,
            current_prices=current_prices,
            portfolio_value=portfolio_value
        )
