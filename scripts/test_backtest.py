#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试回测流程"""

import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer
from analysis.backtester import Backtester

# 加载单个指数数据
analyzer = IndexAnalyzer('000688.SH', start_date='20230101')
analyzer.analyze(include_ml=True)
df = analyzer.data

print("数据列:", df.columns.tolist())
print("\n信号列示例:")
print(df[['trade_date', 'factor_signal', 'ml_signal', 'final_signal']].head(20))

# 测试回测
bt = Backtester(commission_rate=0.00006, execution_timing='close')

# 测试factor_signal
if 'factor_signal' in df.columns:
    print("\n=== 测试 factor_signal 回测 ===")
    result = bt.run(df, signal_column='factor_signal')
    print(f"结果键: {list(result.keys())}")
    print(f"总收益: {result.get('total_return', 'N/A')}")
    print(f"总收益百分比: {result.get('total_return', 0) * 100:.2f}%")
    bt.print_report(result)
