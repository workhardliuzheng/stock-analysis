#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
信号阈值自适应优化 - 简单回测验证
"""
import sys
import os
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer

def simple_test():
    """简单测试"""
    print("=" * 60)
    print("信号阈值自适应优化 - 单指数测试")
    print("=" * 60)
    
    index_code = '000688.SH'  # 科创50
    print(f"\n测试指数: {index_code}")
    
    # 创建分析器
    analyzer = IndexAnalyzer(index_code, start_date='20230101')
    
    # 运行分析
    result = analyzer.analyze(include_ml=True)
    
    if result is not None and len(result) > 0:
        df = result
        print(f"\n[OK] 分析完成")
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
        
        # 显示自适应阈值
        if 'adaptive_buy_threshold' in df.columns:
            print(f"\n自适应阈值:")
            print(f"  BUY > {df['adaptive_buy_threshold'].iloc[-1]*100:.4f}%")
            print(f"  SELL < {df['adaptive_sell_threshold'].iloc[-1]*100:.4f}%")
    else:
        print(f"\n[X] 数据加载失败")
        print(f"result type: {type(result)}")
        print(f"result: {result}")
    
    return result

if __name__ == '__main__':
    try:
        result = simple_test()
        
        print("\n" + "=" * 60)
        print("[DONE] 测试完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
