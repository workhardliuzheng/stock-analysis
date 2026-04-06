#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V7-4 信号阈值优化测试脚本
测试修改后的信号生成逻辑
"""
import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_factor_scorer import MultiFactorScorer
from analysis.backtester import Backtester

def test_single_index():
    """测试单个指数信号分布"""
    print("="*60)
    print("V7-4 信号阈值优化测试")
    print("="*60)
    
    # 测试科创50
    print("\n测试科创50信号分布...")
    analyzer = IndexAnalyzer('000688.SH', start_date='20230101')
    result = analyzer.analyze(include_ml=False)
    
    if result is None or len(result) == 0:
        print("[ERROR] 分析失败")
        return None
    
    # 统计信号分布
    signals = result['final_signal'].value_counts()
    print("\nfinal_signal分布:")
    for signal, count in signals.items():
        print(f"  {signal}: {count} ({count/len(result)*100:.1f}%)")
    
    # 统计factor_score
    scores = result['factor_score']
    print(f"\nfactor_score统计:")
    print(f"  最小值: {scores.min():.2f}")
    print(f"  最大值: {scores.max():.2f}")
    print(f"  平均值: {scores.mean():.2f}")
    print(f"  中位数: {scores.median():.2f}")
    
    # 回测
    print("\n执行回测...")
    bt = Backtester()
    results = bt.run(result, signal_column='final_signal')
    
    print("\n回测结果:")
    print(f"  总收益: {results['total_return']:.2f}%")
    print(f"  夏普比率: {results['sharpe_ratio']:.4f}")
    print(f"  胜率: {results['win_rate']:.2f}%")
    
    return results

def test_portfolio():
    """测试组合回测"""
    print("\n" + "="*70)
    print("组合回测测试")
    print("="*70)
    
    # 8个指数配置
    index_list = [
        ('000688.SH', '科创50', 0.10),
        ('399006.SZ', '创业板指', 0.10),
        ('000001.SH', '上证综指', 0.15),
        ('000905.SH', '中证500', 0.15),
        ('000016.SH', '上证50', 0.10),
        ('000852.SH', '中证1000', 0.10),
    ]
    
    # 加载数据
    print("\n加载数据...")
    df_list = {}
    for code, name, weight in index_list:
        try:
            analyzer = IndexAnalyzer(code, start_date='20230101')
            result = analyzer.analyze(include_ml=False)
            if result is not None and len(result) > 0:
                df_list[code] = result
                print(f"  [OK] {name} ({code}): {len(result)} 行")
            else:
                print(f"  [ERROR] {name} ({code}): 无数据")
        except Exception as e:
            print(f"  [ERROR] {name} ({code}): {e}")
    
    if len(df_list) == 0:
        print("[ERROR] 所有指数加载失败")
        return None
    
    # 合并信号
    common_dates = None
    for code, df in df_list.items():
        if common_dates is None:
            common_dates = df.index
        else:
            common_dates = common_dates.intersection(df.index)
    
    print(f"\n共同日期数: {len(common_dates)}")
    
    # 创建组合
    portfolio_score = 0.0
    portfolio_signal = 0.0
    portfolio_return = 0.0
    
    for code, df in df_list.items():
        df_common = df.loc[common_dates]
        weight = next((w for c, n, w in index_list if c == code), 0.10)
        
        # 计算多因子得分
        scorer = MultiFactorScorer()
        df_with_score = scorer.calculate(df_common)
        
        portfolio_score += df_with_score['factor_score'] * weight
        portfolio_return += df_with_score['pct_chg'] * weight
        
        # 信号处理
        signal_map = {'BUY': 1.0, 'SELL': -1.0, 'HOLD': 0.0}
        portfolio_signal += df_with_score['final_signal'].map(signal_map) * weight
    
    # 创建组合DataFrame
    portfolio_df = df_list[list(df_list.keys())[0]].loc[common_dates].copy()
    portfolio_df['factor_score'] = portfolio_score
    portfolio_df['pct_chg'] = portfolio_return
    portfolio_df['signal'] = portfolio_signal
    
    print(f"\n组合数据行数: {len(portfolio_df)}")
    
    # 回测
    print("\n执行回测...")
    bt = Backtester()
    results = bt.run(portfolio_df, signal_column='signal')
    
    print("\n组合回测结果:")
    print(f"  总收益: {results['total_return']:.2f}%")
    print(f"  夏普比率: {results['sharpe_ratio']:.4f}")
    print(f"  胜率: {results['win_rate']:.2f}%")
    
    return results

if __name__ == '__main__':
    test_single_index()
    test_portfolio()
