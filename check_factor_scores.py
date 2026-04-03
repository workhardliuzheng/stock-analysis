#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速检查多因子评分分布
"""
import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer

# 检查科创50的factor_score分布
print("="*60)
print("科创50 factor_score分布")
print("="*60)

analyzer = IndexAnalyzer('000688.SH', start_date='20230101')
result = analyzer.analyze(include_ml=False)

if result is not None and len(result) > 0:
    print(f"\n数据行数: {len(result)}")
    
    # factor_score统计
    scores = result['factor_score']
    print(f"\nfactor_score统计:")
    print(f"  最小值: {scores.min():.2f}")
    print(f"  最大值: {scores.max():.2f}")
    print(f"  平均值: {scores.mean():.2f}")
    print(f"  中位数: {scores.median():.2f}")
    
    # 信号分布
    signals = result['final_signal'].value_counts()
    print(f"\nfinal_signal分布:")
    for signal, count in signals.items():
        print(f"  {signal}: {count} ({count/len(result)*100:.1f}%)")
    
    # trend_state分布
    if 'trend_state' in result.columns:
        states = result['trend_state'].value_counts()
        print(f"\ntrend_state分布:")
        for state, count in states.items():
            print(f"  {state}: {count} ({count/len(result)*100:.1f}%)")
        
    # 关键发现
    print("\n" + "="*60)
    print("关键发现:")
    print("="*60)
    print(f"  factor_score范围: {scores.min():.2f} - {scores.max():.2f}")
    print(f"  平均得分: {scores.mean():.2f}")
    
    if scores.mean() < 35:
        print("  [INFO] 平均得分低于35，应产生SELL信号")
    elif scores.mean() > 65:
        print("  [INFO] 平均得分高于65，应产生BUY信号")
    else:
        print("  [INFO] 平均得分在35-65之间，产生HOLD信号")
    
    print(f"\n  信号分布: {dict(signals)}")
    print(f"  主要信号: {signals.idxmax()}")
else:
    print("[ERROR] 没有数据")
