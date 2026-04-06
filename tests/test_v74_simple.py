#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V7-4 简单测试 - 单指数信号验证
"""
import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_factor_scorer import MultiFactorScorer
from analysis.signal_threshold_optimizer import SignalThresholdOptimizer
import pandas as pd

# 加载数据
print("加载科创50数据...")
analyzer = IndexAnalyzer('000688.SH', start_date='20230101')
result = analyzer.analyze(include_ml=False)

print(f"数据行数: {len(result)}")

# 计算多因子评分
scorer = MultiFactorScorer()
df = scorer.calculate(result)

print(f"\n原始信号分布:")
original_signals = df['final_signal'].value_counts()
for signal, count in original_signals.items():
    print(f"  {signal}: {count} ({count/len(df)*100:.1f}%)")

# 创建优化器
optimizer = SignalThresholdOptimizer(strategy='aggressive_lite')
print(f"\nV7-4 优化器配置: {optimizer.config}")

# 生成优化信号
print("\n生成优化信号...")
new_signals = []
for i in range(len(df)):
    row = df.iloc[i]
    score = row['factor_score']
    trend_state = row['trend_state']
    volatility = row.get('percentile_20', 1.5)
    
    signal, confidence = optimizer.generate_signal(score, trend_state, volatility=volatility)
    new_signals.append(signal)

# 统计新信号
df['v74_signal'] = new_signals
new_signals_count = df['v74_signal'].value_counts()

print(f"\n优化后信号分布:")
for signal, count in new_signals_count.items():
    print(f"  {signal}: {count} ({count/len(df)*100:.1f}%)")

# 验证信号映射
print(f"\n信号映射验证:")
signal_map = {'BUY': 1.0, 'SELL': -1.0, 'HOLD': 0.0}
signal_numeric = df['v74_signal'].map(signal_map)

print(f"  BUY信号数: {(signal_numeric == 1.0).sum()}")
print(f"  SELL信号数: {(signal_numeric == -1.0).sum()}")
print(f"  HOLD信号数: {(signal_numeric == 0.0).sum()}")

# 检查是否有非零信号
non_zero_signals = signal_numeric[signal_numeric != 0.0]
print(f"\n非零信号统计:")
if len(non_zero_signals) > 0:
    print(f"  最小值: {non_zero_signals.min()}")
    print(f"  最大值: {non_zero_signals.max()}")
    print(f"  总和: {non_zero_signals.sum()}")
else:
    print(f"  [ERROR] 所有信号都是HOLD (数值为0)")
