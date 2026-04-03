#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V7-5 快速测试
"""
import sys
import numpy as np
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_factor_scorer import MultiFactorScorer
from analysis.ml_predictor import MLPredictor
from analysis.adaptive_fusion_optimizer import MetaLearner
import pandas as pd

print("="*60)
print("V7-5 快速测试 - 科创50")
print("="*60)

# 1. 加载数据
print("\n[步骤1] 加载科创50数据...")
analyzer = IndexAnalyzer('000688.SH', start_date='20230101')
result = analyzer.analyze(include_ml=True)

if result is None or len(result) == 0:
    print("[ERROR] 数据加载失败")
    sys.exit(1)

print(f"[OK] 数据行数: {len(result)}")

# 2. 计算多因子评分
print("\n[步骤2] 计算多因子评分...")
scorer = MultiFactorScorer()
df = scorer.calculate(result)

print(f"[OK] 多因子评分完成")
print(f"  factor_score范围: {df['factor_score'].min():.2f} - {df['factor_score'].max():.2f}")
print(f"  factor_signal分布: {df['factor_signal'].value_counts().to_dict()}")

# 3. 训练ML模型
print("\n[步骤3] 训练ML模型...")
predictor = MLPredictor()
df, metrics = predictor.train_and_predict(df, auto_tune=True)

print(f"[OK] ML模型训练完成")
print(f"  MAE: {metrics.get('mae', 0):.4f}")
print(f"  RMSE: {metrics.get('rmse', 0):.4f}")
print(f"  方向准确率: {metrics.get('direction_accuracy', 0):.2f}%")

# 4. 运行Optuna优化
print("\n[步骤4] 运行Optuna优化 (10 trials)...")
meta_learner = MetaLearner(
    initial_train_size=300,
    test_size=60,
    max_trials=10,
    market_state='oscillation'
)

# 确保信号列为数值
df['factor_signal_num'] = df['factor_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)
df['ml_signal_num'] = df['ml_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)

# 优化
weights, sharpe = meta_learner.optimize(df)

print(f"\n{'='*60}")
print("[OK] V7-5 优化完成")
print(f"{'='*60}")
print(f"  最优夏普比率: {sharpe:.4f}")
print(f"  权重分配:")
for key, value in weights.items():
    print(f"    {key}: {value:.2%}")

# 5. 生成融合信号
print("\n[步骤5] 生成融合信号...")
df_fused = meta_learner.generate_fused_signal(df)

print(f"\n[OK] 融合信号生成完成")
print(f"  原始多因子信号: BUY={len(df[df['factor_signal']=='BUY'])} SELL={len(df[df['factor_signal']=='SELL'])} HOLD={len(df[df['factor_signal']=='HOLD'])}")
print(f"  融合后信号: BUY={len(df_fused[df_fused['fused_signal']=='BUY'])} SELL={len(df_fused[df_fused['fused_signal']=='SELL'])} HOLD={len(df_fused[df_fused['fused_signal']=='HOLD'])}")

# 6. 计算回测指标
print("\n[步骤6] 计算回测指标...")
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
print(f"  平均持仓: {(abs(df_fused['position']).sum() / len(df_fused)) * 100:.1f}%")

# 7. 对比
print("\n{'='*60}")
print("[OK] 对比原始vs融合")
print(f"{'='*60}")

# 原始多因子
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
print(f"  夏普比率: {sharpe_final:.4f} {'[↑]' if sharpe_final > sharpe_orig else '[↓]'}")
print(f"  总收益: {cumulative_return:.2f}% {'[↑]' if cumulative_return > ((1 + df_orig['strategy_return']).cumprod().iloc[-1] - 1) * 100 else '[↓]'}")
