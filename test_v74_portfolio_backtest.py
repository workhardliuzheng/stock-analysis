#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V7-4 优化后的组合回测
"""
import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_factor_scorer import MultiFactorScorer
from analysis.signal_threshold_optimizer import SignalThresholdOptimizer
from analysis.backtester import Backtester
import pandas as pd

# 8个指数配置
INDEX_PORTFOLIO = {
    '000688.SH': {'name': '科创50', 'weight': 0.10},
    '399006.SZ': {'name': '创业板指', 'weight': 0.10},
    '000001.SH': {'name': '上证综指', 'weight': 0.15},
    '000905.SH': {'name': '中证500', 'weight': 0.15},
    '000852.SH': {'name': '中证1000', 'weight': 0.10},
}

def run_v74_backtest(index_codes, threshold_optimizer):
    """运行优化后的组合回测"""
    # 1. 加载所有指数
    print("="*80)
    print("加载数据...")
    df_list = {}
    
    for code in index_codes:
        info = INDEX_PORTFOLIO.get(code, {'name': code, 'weight': 1.0/len(index_codes)})
        print(f"  正在分析 {info['name']:>8} ({code})...")
        
        analyzer = IndexAnalyzer(code, start_date='20230101')
        result = analyzer.analyze(include_ml=False)
        
        if result is not None and len(result) > 0:
            # 计算多因子评分
            scorer = MultiFactorScorer()
            df = scorer.calculate(result)
            
            df_list[code] = df
            print(f"    [OK] 加载成功, 行数: {len(df)}")
        else:
            print(f"    [ERROR] 分析失败，跳过")
    
    if len(df_list) == 0:
        print("[ERROR] 没有成功加载的数据")
        return None
    
    # 2. 获取共同日期
    common_dates = None
    for code, df in df_list.items():
        if common_dates is None:
            common_dates = set(df.index)
        else:
            common_dates = common_dates & set(df.index)
    
    common_dates = sorted(list(common_dates))
    
    # 3. 为每个指数生成优化信号
    print(f"\n生成优化信号...")
    portfolio_return = pd.Series(0.0, index=common_dates)
    portfolio_signal = pd.Series(0.0, index=common_dates)
    portfolio_df = None
    
    for code, df in df_list.items():
        info = INDEX_PORTFOLIO.get(code, {'weight': 1.0/len(index_codes)})
        weight = info['weight']
        
        # 限制于共同日期
        df_common = df.loc[common_dates].copy()
        
        # 使用优化器重新生成信号
        new_signals = []
        for i in range(len(df_common)):
            row = df_common.iloc[i]
            score = row['factor_score']
            trend_state = row['trend_state']
            volatility = row.get('percentile_20', 1.5)
            
            signal, confidence = threshold_optimizer.generate_signal(
                score, trend_state, volatility=volatility
            )
            new_signals.append(signal)
        
        df_common['v74_signal'] = new_signals
        
        # 计算加权信号 (BUY=1, SELL=-1, HOLD=0)
        signal_map = {'BUY': 1.0, 'SELL': -1.0, 'HOLD': 0.0}
        signal_numeric = df_common['v74_signal'].map(signal_map)
        
        # 累加
        if portfolio_df is None:
            portfolio_df = pd.DataFrame({
                'trade_date': df_common['trade_date'].values,
                'close': df_common['close'].values,
                'pct_chg': df_common['pct_chg'].values * weight,
                'signal': signal_numeric * weight
            }, index=df_common.index)
        else:
            portfolio_df['pct_chg'] += df_common['pct_chg'].values * weight
            portfolio_df['signal'] += signal_numeric * weight
    
    # 4. 回测
    print(f"\n组合回测...")
    bt = Backtester()
    results = bt.run(portfolio_df, signal_column='signal')
    
    print("\n组合回测结果:")
    print(f"  总收益: {results['total_return']:.2f}%")
    print(f"  年化收益: {results['annualized_return']:.2f}%")
    print(f"  夏普比率: {results['sharpe_ratio']:.4f}")
    print(f"  最大回撤: {results['max_drawdown']:.2f}%")
    print(f"  胜率: {results['win_rate']:.2f}%")
    
    return results


def main():
    """主函数"""
    print("="*80)
    print("V7-4 信号阈值优化 - 组合回测")
    print("="*80)
    
    index_codes = list(INDEX_PORTFOLIO.keys())
    
    # 1. 默认策略 (原始信号)
    print("\n步骤1: 默认策略 (原始信号)")
    print("-"*80)
    
    # 使用默认MultiFactorScorer (无优化)
    analyzer = IndexAnalyzer('000688.SH', start_date='20230101')
    result = analyzer.analyze(include_ml=False)
    scorer = MultiFactorScorer()
    df = scorer.calculate(result)
    
    print(f"\n科创50 默认信号分布:")
    signals = df['final_signal'].value_counts()
    for signal, count in signals.items():
        print(f"  {signal}: {count} ({count/len(df)*100:.1f}%)")
    
    # 自定义回测 (简化版)
    print("\n[SKIP] 默认策略回测 (信号全是HOLD，收益为0)")
    
    # 2. 优化策略 (V7-4)
    print("\n步骤2: 优化策略 (V7-4 aggressive_lite)")
    print("-"*80)
    
    optimizer = SignalThresholdOptimizer(strategy='aggressive_lite')
    results_v74 = run_v74_backtest(index_codes, optimizer)
    
    # 3. 对比
    if results_v74:
        print("\n" + "="*80)
        print("对比结果")
        print("="*80)
        print(f"\nV7-4 优化效果:")
        print(f"  总收益: {results_v74['total_return']:.2f}%")
        print(f"  年化收益: {results_v74['annualized_return']:.2f}%")
        print(f"  夏普比率: {results_v74['sharpe_ratio']:.4f}")
        print(f"  最大回撤: {results_v74['max_drawdown']:.2f}%")
        print(f"  胜率: {results_v74['win_rate']:.2f}%")


if __name__ == '__main__':
    main()
