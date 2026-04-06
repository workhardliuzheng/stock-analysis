#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V7-5 快速测试 - 使用预训练模型
"""
import sys
import numpy as np
sys.path.insert(0, r'E:\pycharm\stock-analysis')

print("="*60)
print("V7-5 自适应融合优化快测")
print("="*60)

# 1. 读取预生成数据
print("\n[步骤1] 读取预生成数据...")
import pandas as pd
try:
    df = pd.read_parquet('E:/pycharm/stock-analysis/data/preprocessed_v7.parquet')
    print(f"[OK] 数据加载完成: {len(df)} 行")
except:
    print("[ERROR] 数据文件不存在，创建示例数据...")
    # 创建示例数据
    df = pd.DataFrame({
        'trade_date': pd.date_range('2023-01-01', periods=500),
        'factor_score': np.random.uniform(30, 70, 500),
        'factor_signal': np.random.choice(['BUY', 'SELL', 'HOLD'], 500, p=[0.2, 0.1, 0.7]),
        'ml_predicted_return': np.random.uniform(-0.05, 0.05, 500),
        'ml_signal': np.random.choice(['BUY', 'SELL', 'HOLD'], 500, p=[0.2, 0.1, 0.7]),
        'pct_chg': np.random.uniform(-0.03, 0.03, 500),
    })
    df['ml_predicted_return'] = df['ml_predicted_return'].fillna(0)
    print(f"[OK] 示例数据创建完成: {len(df)} 行")

# 2. 创建测试用MetaLearner
print("\n[步骤2] 简化版Optuna测试 (5 trials)...")
from analysis.adaptive_fusion_optimizer import MetaLearner

meta_learner = MetaLearner(
    initial_train_size=300,
    test_size=60,
    max_trials=5,
    market_state='oscillation'
)

# 确保信号列为数值
df['factor_signal_num'] = df['factor_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)
df['ml_signal_num'] = df['ml_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)

# 优化
weights, sharpe = meta_learner.optimize(df)

print(f"\n{'='*60}")
print("[OK] 优化完成")
print(f"{'='*60}")
print(f"  最优夏普比率: {sharpe:.4f}")
print(f"  权重分配:")
for key, value in weights.items():
    print(f"    {key}: {value:.2%}")

# 3. 生成融合信号
print("\n[步骤3] 生成融合信号...")
df_fused = meta_learner.generate_fused_signal(df)

# 4. 计算回测指标
print("\n[步骤4] 计算回测指标...")
df_fused['position'] = df_fused['fused_score'].apply(lambda x: 1.0 if x >= 60 else (-1.0 if x < 40 else 0.0))
df_fused['strategy_return'] = df_fused['position'] * df_fused['pct_chg'] / 100

cumulative_return = (1 + df_fused['strategy_return']).cumprod() - 1
cumulative_return = cumulative_return.iloc[-1] * 100

if df_fused['strategy_return'].std() > 0:
    sharpe_final = df_fused['strategy_return'].mean() / df_fused['strategy_return'].std() * np.sqrt(252)
else:
    sharpe_final = 0.0

print(f"\n{'='*60}")
print("[OK] 回测结果")
print(f"{'='*60}")
print(f"  总收益: {cumulative_return:.2f}%")
print(f"  夏普比率: {sharpe_final:.4f}")
print(f"  交易次数: {abs(df_fused['position']).sum():.0f} 次")

# 5. 对比原始多因子
print("\n[步骤5] 对比原始多因子策略...")
df_orig = df.copy()
df_orig['position'] = df_orig['factor_score'].apply(lambda x: 1.0 if x >= 60 else (-1.0 if x < 40 else 0.0))
df_orig['strategy_return'] = df_orig['position'] * df_orig['pct_chg'] / 100

if df_orig['strategy_return'].std() > 0:
    sharpe_orig = df_orig['strategy_return'].mean() / df_orig['strategy_return'].std() * np.sqrt(252)
else:
    sharpe_orig = 0.0

print(f"\n原始多因子策略:")
print(f"  夏普比率: {sharpe_orig:.4f}")
print(f"  总收益: {((1 + df_orig['strategy_return']).cumprod().iloc[-1] - 1) * 100:.2f}%")

print(f"\nV7-5融合策略:")
print(f"  夏普比率: {sharpe_final:.4f} {'[↑ 更优]' if sharpe_final > sharpe_orig else '[↓ 较差]'}")
print(f"  总收益: {cumulative_return:.2f}% {'[↑ 更优]' if cumulative_return > ((1 + df_orig['strategy_return']).cumprod().iloc[-1] - 1) * 100 else '[↓ 较差]'}")
