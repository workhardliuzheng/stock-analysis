#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查2021-2022年熊市期间的信号分布"""

import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer

def check_signals():
    codes = {
        '000688.SH': '科创50',
        '399006.SZ': '创业板指',
        '000001.SH': '上证综指',
        '000300.SH': '沪深300',
    }
    
    for code, name in codes.items():
        print(f"\n{'='*60}")
        print(f"{name} ({code}) - 2021-2022年熊市")
        print(f"{'='*60}")
        
        analyzer = IndexAnalyzer(code, start_date='20210101')
        analyzer.analyze(include_ml=False, auto_tune=False)
        
        # 过滤日期范围
        analyzer.data = analyzer.data[
            (analyzer.data['trade_date'] >= '2021-01-01') & 
            (analyzer.data['trade_date'] <= '2022-12-31')
        ]
        
        # 信号分布
        print(f"final_signal分布:")
        print(analyzer.data['final_signal'].value_counts())
        print()
        
        # 买入持有收益
        buy_hold = (analyzer.data['close'].iloc[-1] - analyzer.data['close'].iloc[0]) / analyzer.data['close'].iloc[0]
        print(f"买入持有收益: {buy_hold*100:+.2f}%")

if __name__ == "__main__":
    check_signals()
