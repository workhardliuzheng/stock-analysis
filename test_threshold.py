import pandas as pd
import numpy as np
from analysis.ml_predictor import MLPredictor

# 测试自适应阈值
predictor = MLPredictor()
returns = pd.Series(np.random.randn(100) * 1.5)  # 模拟波动率1.5%

# 测试基础功能
thresh, sell = predictor._calculate_adaptive_thresholds(returns)
print(f'基础阈值: BUY>{thresh:.4f}%, SELL<{sell:.4f}%')

# 测试市场波动率调整
thresh2, sell2 = predictor._calculate_adaptive_thresholds(returns, market_volatility=1.5)
print(f'高市场波动: BUY>{thresh2:.4f}%, SELL<{sell2:.4f}%')

# 测试交易频率调整
thresh3, sell3 = predictor._calculate_adaptive_thresholds(returns, recent_trade_frequency=0.4)
print(f'高交易频率: BUY>{thresh3:.4f}%, SELL<{sell3:.4f}%')

# 测试综合调整
thresh4, sell4 = predictor._calculate_adaptive_thresholds(returns, market_volatility=1.5, recent_trade_frequency=0.4)
print(f'综合调整: BUY>{thresh4:.4f}%, SELL<{sell4:.4f}%')
