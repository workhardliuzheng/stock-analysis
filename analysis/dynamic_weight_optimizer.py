"""
动态权重优化模块

使用 Optuna 在回测框架内搜索最优多因子权重组合
支持市场状态识别与自适应权重调整
"""

from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
import optuna
from optuna.trial import Trial
from datetime import datetime

from analysis.multi_factor_scorer import MultiFactorScorer
from analysis.backtester import Backtester


class DynamicWeightOptimizer:
    """
    动态权重优化器
    
    功能:
    1. 使用 Optuna 优化器搜索最优多因子权重
    2. 支持市场状态识别与自适应权重调整
    3. 滚动优化：定期更新权重参数
    
    权重定义:
        - trend: 趋势因子 (基准 30%)
        - momentum: 动量因子 (基准 25%)
        - volume: 成交量因子 (基准 15%)
        - valuation: 估值因子 (基准 20%)
        - volatility: 波动率因子 (基准 10%)
    """
    
    # 权重搜索空间
    WEIGHT_RANGES = {
        'trend': (0.15, 0.45),      # 15%-45%
        'momentum': (0.15, 0.40),   # 15%-40%
        'volume': (0.05, 0.25),     # 5%-25%
        'valuation': (0.10, 0.35),  # 10%-35%
        'volatility': (0.05, 0.20)  # 5%-20%
    }
    
    # 市场状态定义
    MARKET_STATES = {
        'bull': {'increase': 0.6, 'decrease': 0.4},    # 牛市：高收益，高风险
        'bear': {'increase': 0.3, 'decrease': 0.7},    # 熊市：低收益，低风险
        '震荡': {'increase': 0.4, 'decrease': 0.6},     # 震荡：收益适中，风险适中
    }
    
    def __init__(self, n_trials: int = 50, window_size: int = 250):
        """
        Args:
            n_trials: Optuna 优化次数
            window_size: 滚动窗口大小（交易日）
        """
        self.n_trials = n_trials
        self.window_size = window_size
        self.best_weights = None
        self.market_state_weights = None
    
    def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """确保权重和为1"""
        total = sum(weights.values())
        return {k: v/total for k, v in weights.items()}
    
    def _objective(self, trial: Trial, df: pd.DataFrame) -> float:
        """
        Optuna 优化目标函数
        
        Args:
            trial: Optuna trial 对象
            df: 回测数据
            
        Returns:
            float: 优化目标值（夏普比率）
        """
        # 采样权重
        weights = {}
        for factor, (min_w, max_w) in self.WEIGHT_RANGES.items():
            weights[factor] = trial.suggest_float(factor, min_w, max_w)
        
        # 归一化
        weights = self._normalize_weights(weights)
        
        # 计算评分
        scorer = MultiFactorScorer(weights=weights)
        
        try:
            df_scored = scorer.calculate(df.copy())
            
            # 确保存在 final_signal 列
            if 'final_signal' not in df_scored.columns:
                # 如果没有 final_signal，使用 factor_signal
                if 'factor_signal' in df_scored.columns:
                    df_scored['final_signal'] = df_scored['factor_signal']
                else:
                    return -1e6
            
            # 回测
            backtester = Backtester()
            result = backtester.run(
                df=df_scored,
                signal_column='final_signal'
            )
            
            # 获取夏普比率
            sharpe = result.get('sharpe_ratio', 0.0)
            
            # 如果数据不足，返回负无穷
            if sharpe is None or np.isnan(sharpe) or sharpe == 0:
                return -1e6
            
            return float(sharpe)
            
        except Exception as e:
            print(f"  优化异常: {e}")
            return -1e6
            
            # 获取夏普比率
            metrics = result.get('metrics', {})
            sharpe = metrics.get('sharpe_ratio', 0.0)
            
            # 如果数据不足，返回负无穷
            if np.isnan(sharpe) or sharpe == 0:
                return -1e6
            
            return sharpe
            
        except Exception as e:
            return -1e6
    
    def optimize(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        优化多因子权重
        
        Args:
            df: 回测数据
            
        Returns:
            Dict[str, float]: 最优权重字典
        """
        print("正在优化多因子权重...")
        
        # 定义 Optuna study
        study = optuna.create_study(direction='maximize')
        
        # 优化
        study.optimize(
            lambda trial: self._objective(trial, df),
            n_trials=self.n_trials,
            show_progress_bar=True
        )
        
        # 获取最优权重
        best_params = study.best_params
        self.best_weights = self._normalize_weights(best_params)
        
        print(f"最优权重: {self.best_weights}")
        print(f"最优夏普比率: {study.best_value:.4f}")
        
        return self.best_weights
    
    def analyze_market_state(self, df: pd.DataFrame) -> str:
        """
        分析当前市场状态
        
        基于:
        - MA200方向
        - 波动率水平
        - 趋势强度
        
        Args:
            df: 回测数据
            
        Returns:
            str: 市场状态 (bull/bear/震荡)
        """
        if len(df) < 50:
            return '震荡'
        
        latest = df.iloc[-1]
        
        # 尝试多个可能的列名
        ma200_cols = ['ma_200', 'MA_200', 'ma200', 'MA200']
        ma200 = None
        for col in ma200_cols:
            if col in df.columns:
                ma200 = df[col]
                break
        
        ma200_slope = ma200.diff().iloc[-10:].mean() if ma200 is not None else 0
        
        # 波动率
        returns_std = df['pct_chg'].iloc[-20:].std()
        
        # 趋势强度 (通过ADXR或ADX)
        adxr_cols = ['adxr', 'ADXr', 'ADXR', 'adx', 'ADX']
        trend_strength = 20
        for col in adxr_cols:
            if col in latest.index and not pd.isna(latest[col]):
                trend_strength = latest[col]
                break
        
        # 判断市场状态
        if ma200_slope > 0 and returns_std < 1.0 and trend_strength > 25:
            return 'bull'  # 牛市
        elif ma200_slope < 0 and returns_std > 1.5:
            return 'bear'  # 熊市
        else:
            return '震荡'
    
    def get_adaptive_weights(self, market_state: str) -> Dict[str, float]:
        """
        根据市场状态获取自适应权重
        
        Args:
            market_state: 市场状态 (bull/bear/震荡)
            
        Returns:
            Dict[str, float]: 适应性权重
        """
        if self.market_state_weights is None:
            # 默认权重
            self.market_state_weights = {
                'bull': {
                    'trend': 0.35,      # 牛市趋势重要性高
                    'momentum': 0.30,   # 牛市动量持续性强
                    'volume': 0.15,
                    'valuation': 0.10,  # 牛市可以适当降低估值关注
                    'volatility': 0.10
                },
                'bear': {
                    'trend': 0.25,      # 熊市趋势弱化
                    'momentum': 0.15,   # 熊市动量反转快
                    'volume': 0.20,     # 熊市成交量更重要
                    'valuation': 0.25,  # 熊市关注估值bottom
                    'volatility': 0.15
                },
                '震荡': {
                    'trend': 0.30,
                    'momentum': 0.25,
                    'volume': 0.15,
                    'valuation': 0.20,
                    'volatility': 0.10
                }
            }
        
        return self.market_state_weights.get(market_state, self.market_state_weights['震荡'])


def optimize_multi_factor_weights(df: pd.DataFrame, 
                                   n_trials: int = 50,
                                   save_path: Optional[str] = None) -> Dict[str, float]:
    """
    优化多因子权重 (封装函数)
    
    Args:
        df: 回测数据
        n_trials: Optuna优化次数
        save_path: 保存最优权重的路径
        
    Returns:
        Dict[str, float]: 最优权重
    """
    optimizer = DynamicWeightOptimizer(n_trials=n_trials)
    best_weights = optimizer.optimize(df)
    
    if save_path:
        import json
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(best_weights, f, ensure_ascii=False, indent=2)
        print(f"最优权重已保存到: {save_path}")
    
    return best_weights
