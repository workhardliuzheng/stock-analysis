#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
信号阈值自适应优化 - 完整回测验证脚本
"""
import sys
import os
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_index_backtester import MultiIndexBacktester

def run_full_backtest():
    """运行完整回测"""
    print("=" * 80)
    print("信号阈值自适应优化 - 完整回测验证")
    print("=" * 80)
    
    # 测试所有8个指数
    indices = [
        ('000688.SH', '科创50'),
        ('000905.SH', '中证500'),
        ('000852.SH', '中证1000'),
        ('399006.SZ', '创业板指'),
        ('000016.SH', '上证50'),
        ('000300.SH', '沪深300'),
        ('000001.SH', '上证综指'),
        ('399106.SZ', '深证成指'),
    ]
    
    # 准备数据
    df_list = []
    code_list = []
    name_list = []
    
    for idx_code, idx_name in indices:
        print(f"正在加载 {idx_name} ({idx_code}) 数据...")
        try:
            analyzer = IndexAnalyzer(idx_code, start_date='20230101')
            result = analyzer.analyze(include_ml=True)
            
            if 'data' in result and len(result['data']) > 0:
                df = result['data']
                df_list.append(df)
                code_list.append(idx_code)
                name_list.append(idx_name)
                print(f"  ✅ 加载成功: {len(df)} 行数据")
            else:
                print(f"  ❌ 加载失败: {idx_name}")
                
        except Exception as e:
            print(f"  ❌ 加载失败: {idx_name} - {e}")
    
    if not df_list:
        print("\n错误: 没有成功加载任何指数数据")
        return {}
    
    print(f"\n成功加载 {len(df_list)}/{len(indices)} 个指数数据")
    
    # 运行回测
    print("\n" + "=" * 80)
    print("开始回测...")
    print("=" * 80)
    
    from analysis.multi_index_backtester import MultiIndexBacktester
    
    backtester = MultiIndexBacktester(
        initial_capital=100000,
        commission_rate=0.00006
    )
    
    results = backtester.run(
        df_list=df_list,
        code_list=code_list,
        name_list=name_list,
        use_ml_signals=True,
        use_market_timing=True
    )
    
    # 打印详细结果
    print("\n" + "=" * 80)
    print("回测结果汇总")
    print("=" * 80)
    
    for idx, result in results.items():
        print(f"\n{idx}:")
        if 'metrics' in result:
            metrics = result['metrics']
            print(f"  总收益: {metrics.get('total_return', 0)*100:.2f}%")
            print(f"  年化收益: {metrics.get('annual_return', 0)*100:.2f}%")
            print(f"  最大回撤: {metrics.get('max_drawdown', 0)*100:.2f}%")
            print(f"  夏普比率: {metrics.get('sharpe_ratio', 0):.3f}")
            print(f"  信号数量: {metrics.get('signal_count', 0)}")
    
    return results

if __name__ == '__main__':
    try:
        results = run_full_backtest()
        
        print("\n" + "=" * 80)
        print("✨ 回测完成!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
