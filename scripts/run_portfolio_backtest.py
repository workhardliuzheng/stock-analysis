#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多指数分仓回测 - 模拟真实投资组合
每个指数分配一定仓位，动态优化权重
"""
import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_factor_scorer import MultiFactorScorer
from analysis.dynamic_weight_optimizer import DynamicWeightOptimizer
from analysis.backtester import Backtester
import pandas as pd
import numpy as np
import json

# 8个指数配置 (根据市值分配权重)
INDEX_PORTFOLIO = {
    '000688.SH': {'name': '科创50', 'weight': 0.10},   # 10%
    '399006.SZ': {'name': '创业板指', 'weight': 0.10},  # 10%
    '000001.SH': {'name': '上证综指', 'weight': 0.15},  # 15%
    '000300.SH': {'name': '沪深300', 'weight': 0.20},   # 20% (修正代码)
    '000905.SH': {'name': '中证500', 'weight': 0.15},   # 15%
    '399001.SZ': {'name': '深证成指', 'weight': 0.10},  # 10% (修正代码)
    '000016.SH': {'name': '上证50', 'weight': 0.10},   # 10%
    '000852.SH': {'name': '中证1000', 'weight': 0.10},  # 10%
}

def analyze_single_index(index_code):
    """分析单个指数"""
    try:
        analyzer = IndexAnalyzer(index_code, start_date='20230101')
        result = analyzer.analyze(include_ml=False)
        return result
    except Exception as e:
        print(f"[ERROR] {index_code} 分析失败: {str(e)[:100]}")
        return None

def run_portfolio_backtest(use_optimized_weights=False):
    """运行组合回测"""
    print("="*80)
    print("多指数分仓回测 - V7-3 动态权重优化验证")
    print("="*80)
    
    # 1. 分析所有指数
    print("\n步骤1: 加载数据...")
    df_list = {}
    for code, info in INDEX_PORTFOLIO.items():
        print(f"  正在分析 {info['name']:>8} ({code})...")
        df = analyze_single_index(code)
        if df is not None and len(df) > 0:
            df_list[code] = df
            print(f"    [OK] 加载成功，数据行数: {len(df)}")
        else:
            print(f"    [ERROR] 分析失败，跳过")
    
    print(f"\n[OK] 共加载 {len(df_list)}/{len(INDEX_PORTFOLIO)} 个指数数据")
    
    if len(df_list) == 0:
        print("[ERROR] 没有成功加载的数据")
        return None
    
    # 2. 获取最优权重（如果启用）
    best_weights = None
    if use_optimized_weights:
        print("\n步骤2: 优化权重（科创50参考）...")
        optimizer = DynamicWeightOptimizer(n_trials=20)
        df_ref = df_list['000688.SH']
        best_weights = optimizer.optimize(df_ref)
        print(f"[OK] 最优权重: {best_weights}")
    
    # 3. 为每个指数计算得分
    print(f"\n步骤3: 计算各指数得分...")
    
    # 获取日期范围
    common_dates = None
    for code, df in df_list.items():
        if common_dates is None:
            common_dates = set(df.index)
        else:
            common_dates = common_dates & set(df.index)
    
    common_dates = sorted(list(common_dates))
    print(f"[OK] 共同日期范围: {common_dates[0]} ~ {common_dates[-1]}")
    
    # 为每个指数计算加权得分
    index_scores = {}
    for code, info in INDEX_PORTFOLIO.items():
        if code not in df_list:
            continue
        df = df_list[code]
        
        # 限于共同日期
        df_common = df.loc[common_dates]
        
        # 保留必要列（Backtester需要）
        columns_to_keep = ['trade_date', 'close', 'pct_chg', 'factor_score', 'final_signal']
        available_cols = [c for c in columns_to_keep if c in df_common.columns]
        if 'close' not in df_common.columns:
            print(f"    [ERROR] {info['name']} 缺少close列")
            continue
        
        # 使用优化权重或默认权重
        weights = best_weights if use_optimized_weights else {
            'trend': 0.30, 'momentum': 0.25, 'volume': 0.15,
            'valuation': 0.20, 'volatility': 0.10
        }
        
        scorer = MultiFactorScorer(weights=weights)
        df_with_score = scorer.calculate(df_common[available_cols])
        
        index_scores[code] = {
            'name': info['name'],
            'weight': info['weight'],
            'factor_score': df_with_score['factor_score'],
            'trade_date': df_with_score['trade_date'],
            'close': df_with_score['close'],
            'pct_chg': df_with_score['pct_chg'] / 100.0,
            'signal': df_with_score['final_signal']
        }
        
        print(f"  {info['name']:>8}: {index_scores[code]['factor_score'].mean():6.2f}分")
    
    # 4. 计算组合得分
    print(f"\n步骤4: 创建投资组合...")
    
    # 初始化组合DataFrame
    portfolio_df = pd.DataFrame(index=common_dates)
    
    # 从第一个指数获取基础列
    first_code = list(index_scores.keys())[0]
    portfolio_df['trade_date'] = index_scores[first_code]['trade_date'].values
    portfolio_df['close'] = index_scores[first_code]['close'].values
    portfolio_df['pct_chg'] = index_scores[first_code]['pct_chg'].values * index_scores[first_code]['weight']
    
    # 计算组合得分（加权平均）
    portfolio_score = pd.Series(0.0, index=common_dates)
    portfolio_signal_map = {'BUY': 1.0, 'SELL': -1.0, 'HOLD': 0.0}
    portfolio_signal = pd.Series(0.0, index=common_dates, dtype=float)
    
    for code, data in index_scores.items():
        weight = data['weight']
        portfolio_score += data['factor_score'] * weight
        portfolio_signal += data['signal'].map(portfolio_signal_map) * weight
        portfolio_df['pct_chg'] += data['pct_chg'] * weight
    
    print(f"[OK] 组合数据行数: {len(portfolio_df)}")
    
    # 添加信号列到组合DataFrame
    portfolio_df['signal'] = portfolio_signal.values
    portfolio_df['final_signal'] = portfolio_signal.map({1.0: 'BUY', -1.0: 'SELL', 0.0: 'HOLD'})
    print(f"[OK] 信号列已添加")
    
    # 5. 回测组合
    print("\n步骤5: 回测组合...")
    bt = Backtester()
    
    # 确定信号列
    signal_col = 'signal'
    if signal_col not in portfolio_df.columns:
        signal_col = 'final_signal'
        if signal_col not in portfolio_df.columns:
            print(f"[ERROR] 找不到信号列，可用列: {list(portfolio_df.columns)}")
            return None
    
    results = bt.run(portfolio_df, signal_column=signal_col)
    
    print("\n组合回测结果:")
    print(f"  总收益: {results['total_return']:.2f}%")
    print(f"  年化收益: {results['annualized_return']:.2f}%")
    print(f"  最大回撤: {results['max_drawdown']:.2f}%")
    print(f"  夏普比率: {results['sharpe_ratio']:.4f}")
    print(f"  胜率: {results['win_rate']:.2f}%")
    
    # 6. 对比结果（如果启用优化）
    if use_optimized_weights:
        print("\n步骤6: 对比优化前/后...")
        results_default = run_portfolio_backtest(use_optimized_weights=False)
        
        if results_default:
            print("\n对比结果:")
            print(f"  默认夏普: {results_default['sharpe_ratio']:>8.4f} -> 优化夏普: {results['sharpe_ratio']:>8.4f}")
            print(f"  夏普提升: {results['sharpe_ratio'] - results_default['sharpe_ratio']:+.4f}")
            print(f"  总收益提升: {results['total_return'] - results_default['total_return']:+.2f}%")
            
            return {
                'default_sharpe': results_default['sharpe_ratio'],
                'optimized_sharpe': results['sharpe_ratio'],
                'improvement': results['sharpe_ratio'] - results_default['sharpe_ratio'],
                'total_return': results['total_return'],
                'weights': best_weights
            }
    
    return {
        'sharpe_ratio': results['sharpe_ratio'],
        'total_return': results['total_return'],
        'weights': best_weights if use_optimized_weights else None
    }

def main():
    """主函数"""
    print("="*80)
    print("多指数分仓回测")
    print("="*80)
    
    # 组合配置
    print("\n投资组合配置:")
    for code, info in INDEX_PORTFOLIO.items():
        print(f"  {info['name']:>8} ({code}): {info['weight']*100:5.1f}%")
    print(f"\n组合总仓位: 100.0%")
    
    # 默认权重回测
    print("\n" + "="*80)
    print("步骤1: 默认权重回测")
    print("="*80)
    results_default = run_portfolio_backtest(use_optimized_weights=False)
    
    # 优化权重回测
    print("\n" + "="*80)
    print("步骤2: 优化权重回测")
    print("="*80)
    results_optimized = run_portfolio_backtest(use_optimized_weights=True)
    
    # 最终报告
    if results_default and results_optimized:
        print("\n" + "="*80)
        print("最终报告 - 多指数分仓回测")
        print("="*80)
        
        print("\n回测对比:")
        print(f"  指标              默认权重    优化权重    对比")
        print(f"  总收益            {results_default['total_return']:8.2f}%  {results_optimized['total_return']:8.2f}%  {results_optimized['total_return']-results_default['total_return']:+.2f}%")
        print(f"  夏普比率          {results_default['sharpe_ratio']:8.4f}   {results_optimized['optimized_sharpe']:8.4f}   {results_optimized['improvement']:+.4f}")
        
        print("\n权重分布优化:")
        if results_optimized.get('weights'):
            print("  默认: trend=30%, momentum=25%, volume=15%, valuation=20%, volatility=10%")
            for factor, weight in results_optimized['weights'].items():
                print(f"  优化: {factor:<10}: {weight*100:6.1f}%")
        
        print("\n结论:")
        improvement = results_optimized['improvement']
        if improvement > 0.01:
            print(f"  [OK] 优化有效！夏普比率提升 {improvement:.4f}")
        elif improvement > 0:
            print(f"  [WARN] 优化效果微弱，夏普比率提升 {improvement:.4f}")
        else:
            print(f"  [WARN] 优化无效，夏普比率下降 {abs(improvement):.4f}")

if __name__ == '__main__':
    main()
