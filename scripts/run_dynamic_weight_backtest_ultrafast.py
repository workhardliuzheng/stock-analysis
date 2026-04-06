#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
动态权重调整 - 超快回测 (仅1个指数快速验证)
"""
import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_factor_scorer import MultiFactorScorer
from analysis.dynamic_weight_optimizer import DynamicWeightOptimizer
from analysis.backtester import Backtester

def ultra_fast_backtest():
    """超快回测科创50 (10 trials, 简化计算)"""
    print("="*70)
    print("动态权重调整 - 超快回测验证")
    print("="*70)
    
    index_code = '000688.SH'
    index_name = '科创50'
    n_trials = 10  # 减少到10 trials
    
    print(f"\n[OK] 回测指数: {index_name} ({index_code})")
    print(f"[OK] 试验次数: {n_trials}")
    
    try:
        # 1. 加载数据
        print("[OK] 加载数据...")
        analyzer = IndexAnalyzer(index_code, start_date='20230101')
        result = analyzer.analyze(include_ml=False)
        df = result
        print(f"[OK] 数据行数: {len(df)}")
        
        # 2. 默认权重
        print("\n[OK] 默认权重...")
        scorer_def = MultiFactorScorer()
        df_def = scorer_def.calculate(df)
        bt = Backtester()
        results_def = bt.run(df_def, signal_column='final_signal')
        print(f"[OK] 夏普比率: {results_def['sharpe_ratio']:.4f}")
        
        # 3. 优化权重
        print(f"\n[OK] 优化权重 (n_trials={n_trials})...")
        optimizer = DynamicWeightOptimizer(n_trials=n_trials)
        best_weights = optimizer.optimize(df)
        
        print("\n[OK] 最优权重:")
        for factor, weight in best_weights.items():
            print(f"  {factor:<10}: {weight*100:6.1f}%")
        
        # 4. 优化后回测
        print("\n[OK] 优化后回测...")
        scorer_opt = MultiFactorScorer(weights=best_weights)
        df_opt = scorer_opt.calculate(df)
        results_opt = bt.run(df_opt, signal_column='final_signal')
        
        print(f"[OK] 夏普比率: {results_opt['sharpe_ratio']:.4f}")
        print(f"[OK] 改善: {results_opt['sharpe_ratio'] - results_def['sharpe_ratio']:+.4f}")
        
        print("\n" + "="*70)
        print("[OK] 超快回测完成！")
        print("="*70)
        
        return {
            'index': index_name,
            'default_sharpe': results_def['sharpe_ratio'],
            'optimized_sharpe': results_opt['sharpe_ratio'],
            'improvement': results_opt['sharpe_ratio'] - results_def['sharpe_ratio'],
            'weights': best_weights,
            'market_state': optimizer.market_state
        }
        
    except Exception as e:
        print(f"\n[ERROR] 失败: {str(e)[:100]}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    ultra_fast_backtest()
