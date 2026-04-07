#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试Backtester"""

import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer
from analysis.backtester import Backtester

# 加载数据
a = IndexAnalyzer('000688.SH')
df = a.analyze()

# 创建position列
df['pos'] = (df['factor_score'] >= 50).astype(int) - (df['factor_score'] < 50).astype(int)

print("position分布:", df['pos'].value_counts())

# 运行回测
bt = Backtester()
result = bt.run(df, signal_column='pos')

print("结果键:", list(result.keys()))
print("总收益:", result.get('total_return', 0))
print("夏普比率:", result.get('sharpe_ratio', 0))
print("交易次数:", len(result.get('trades', [])))
