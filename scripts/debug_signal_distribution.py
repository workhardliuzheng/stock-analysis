#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""调试信号分布"""

import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from entity import constant
from analysis.index_analyzer import IndexAnalyzer

# 加载科创50
analyzer = IndexAnalyzer('000688.SH', start_date='20230101')
df = analyzer.analyze(include_ml=True, auto_tune=False)

print("信号分布:")
print("factor_signal:", df['factor_signal'].value_counts())
print("ml_signal:", df['ml_signal'].value_counts())
print("final_signal:", df['final_signal'].value_counts())

# 计算权重
weights = {
    'factor_score': 0.7,
    'factor_signal': 0.05,
    'ml_return': 0.2,
    'ml_signal': 0.05,
}

# 预处理
df['factor_signal_num'] = df['factor_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)
df['ml_signal_num'] = df['ml_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)

# 计算fused_score
df['fused_score'] = (
    weights['factor_score'] * df['factor_score'] +
    weights['factor_signal'] * df['factor_signal_num'] * 50 +
    weights['ml_return'] * df['ml_predicted_return'] * 100 +
    weights['ml_signal'] * df['ml_signal_num'] * 50
)

print("\nfused_score分布:")
print(df['fused_score'].describe())

print("\nfused_score信号分布:")
print("BUY(>=60):", len(df[df['fused_score'] >= 60]))
print("SELL(<40):", len(df[df['fused_score'] < 40]))
print("HOLD(40-60):", len(df[(df['fused_score'] >= 40) & (df['fused_score'] < 60)]))

print("\nPosition分布:")
df['position'] = 0
df.loc[df['fused_score'] >= 60, 'position'] = 1
df.loc[df['fused_score'] < 40, 'position'] = -1
print(df['position'].value_counts())
