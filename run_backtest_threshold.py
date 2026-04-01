#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
信号阈值自适应优化 - 回测验证脚本
"""
import sys
import os
sys.path.insert(0, r'E:\pycharm\stock-analysis')

# 导入必要模块
from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_index_backtester import MultiIndexBacktester
import traceback

def run_backtest():
    """运行回测"""
    print("=" * 60)
    print("信号阈值自适应优化 - 回测验证")
    print("=" * 60)
    
    indices = [
        '000688.SH',  # 科创50
        '000905.SH',  # 中证500
        '000852.SH',  # 中证1000
    ]
    
    results_all = {}
    
    for index_code in indices:
        print(f"\n{'='*60}")
        print(f"回测指数: {index_code}")
        print('='*60)
        
        try:
            # 创建分析器
            analyzer = IndexAnalyzer(index_code, start_date='20230101')
            
            # 运行分析
            result = analyzer.analyze(include_ml=True)
            
            if 'data' in result and len(result['data']) > 0:
                df = result['data']
                print(f"数据行数: {len(df)}")
                
                # 统计信号
                if 'ml_signal' in df.columns:
                    signals = df['ml_signal'].value_counts()
                    print(f"\n信号分布:")
                    for sig, count in signals.items():
                        print(f"  {sig}: {count}")
                
                # 计算收益
                if 'strategy_returns' in df.columns:
                    total_return = (1 + df['strategy_returns']).prod() - 1
                    print(f"\n策略总收益: {total_return*100:.2f}%")
                
                results_all[index_code] = result
                
        except Exception as e:
            print(f"错误: {e}")
            traceback.print_exc()
    
    return results_all

if __name__ == '__main__':
    try:
        results = run_backtest()
        
        print("\n" + "=" * 60)
        print("回测完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n严重错误: {e}")
        traceback.print_exc()
        sys.exit(1)
