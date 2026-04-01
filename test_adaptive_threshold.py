#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
信号阈值自适应优化 - 回测验证
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_index_backtester import MultiIndexBacktester
import pandas as pd

def test_single_index():
    """测试单个指数"""
    print("=" * 60)
    print("测试信号阈值自适应优化 - 科创50")
    print("=" * 60)
    
    analyzer = IndexAnalyzer('000688.SH', start_date='20230101')
    result = analyzer.analyze(include_ml=True)
    
    if 'data' in result:
        df = result['data']
        print(f"\n数据行数: {len(df)}")
        if 'ml_signal' in df.columns:
            signals = df['ml_signal'].value_counts()
            print(f"\n信号分布:")
            print(signals)
    
    return result

def run_backtest():
    """运行回测"""
    print("\n" + "=" * 60)
    print("运行回测验证")
    print("=" * 60)
    
    indices = ['000688.SH']  # 先测试一个指数
    
    backtester = MultiIndexBacktester(
        indices=indices,
        start_date='20230101',
        end_date='20251231',
        strategy='ml',
        position_size=1.0
    )
    
    results = backtester.run_backtest()
    
    print("\n回测结果:")
    for idx, result in results.items():
        print(f"\n{idx}:")
        if 'metrics' in result:
            metrics = result['metrics']
            print(f"  总收益: {metrics.get('total_return', 0):.2f}%")
            print(f"  年化收益: {metrics.get('annual_return', 0):.2f}%")
            print(f"  最大回撤: {metrics.get('max_drawdown', 0):.2f}%")
            print(f"  夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
    
    return results

if __name__ == '__main__':
    try:
        # 测试单个指数
        result = test_single_index()
        
        # 运行回测
        backtest_results = run_backtest()
        
        print("\n" + "=" * 60)
        print("测试完成!")
        print("=" * 60)
        
    except Exception as e:
        import traceback
        print(f"\n错误: {e}")
        traceback.print_exc()
