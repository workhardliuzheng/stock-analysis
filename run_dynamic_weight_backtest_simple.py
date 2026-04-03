#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
动态权重调整优化 - 简化回测脚本 (快速验证)
"""
import sys
import os
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_factor_scorer import MultiFactorScorer
from analysis.dynamic_weight_optimizer import DynamicWeightOptimizer
from analysis.backtester import Backtester

def run_backtest_for_index(index_code, index_name, start_date='20230101'):
    """单个指数回测"""
    print(f"\n{'='*80}")
    print(f"回测指数: {index_name} ({index_code})")
    print('='*80)
    
    try:
        # 1. 创建分析器
        analyzer = IndexAnalyzer(index_code, start_date=start_date)
        result = analyzer.analyze(include_ml=False)
        
        if result is None or len(result) == 0:
            print(f"[ERROR] 分析失败")
            return None
        
        df = result
        print(f"[OK] 数据行数: {len(df)}")
        
        # 2. 使用默认权重
        print("\n步骤1: 使用默认权重计算...")
        scorer_default = MultiFactorScorer(weights=None)  # 默认权重
        df_default = scorer_default.calculate(df)
        
        # 3. 回测默认权重
        backtester = Backtester()
        results_default = backtester.run(df_default, signal_column='final_signal')
        
        print("\n默认权重回测结果:")
        print(f"  总收益: {results_default['total_return']*100:.2f}%")
        print(f"  年化收益: {results_default['annual_return']*100:.2f}%")
        print(f"  最大回撤: {results_default['max_drawdown']*100:.2f}%")
        print(f"  夏普比率: {results_default['sharpe_ratio']:.4f}")
        print(f"  胜率: {results_default['win_rate']*100:.2f}%")
        
        # 4. 优化多因子权重（50 trials）
        print("\n步骤2: 优化多因子权重...")
        optimizer = DynamicWeightOptimizer()
        best_weights, best_value, trials_results = optimizer.optimize(
            df, n_trials=50, verbose=True
        )
        
        print("\n最优权重:")
        total_weight = sum(best_weights.values())
        for factor, weight in best_weights.items():
            print(f"  {factor:<12}: {weight*100:6.1f}% ({weight*100/total_weight:6.1f}%)")
        print(f"  总和: {total_weight*100:.1f}%")
        
        # 5. 回测优化后权重
        print("\n步骤3: 回测优化后权重...")
        scorer_optimized = MultiFactorScorer(weights=best_weights)
        df_optimized = scorer_optimized.calculate(df)
        
        results_optimized = backtester.run(df_optimized, signal_column='final_signal')
        
        print("\n优化后权重回测结果:")
        print(f"  总收益: {results_optimized['total_return']*100:.2f}%")
        print(f"  年化收益: {results_optimized['annual_return']*100:.2f}%")
        print(f"  最大回撤: {results_optimized['max_drawdown']*100:.2f}%")
        print(f"  夏普比率: {results_optimized['sharpe_ratio']:.4f}")
        print(f"  胜率: {results_optimized['win_rate']*100:.2f}%")
        
        # 6. 对比结果
        print("\n步骤4: 对比优化前/后效果...")
        print(f"  夏普比率变化: {results_optimized['sharpe_ratio'] - results_default['sharpe_ratio']:+.4f}")
        print(f"  总收益变化: {(results_optimized['total_return'] - results_default['total_return'])*100:+.2f}%")
        
        return {
            'index_code': index_code,
            'index_name': index_name,
            'default_weights': {
                'trend': 0.30, 'momentum': 0.25, 'volume': 0.15,
                'valuation': 0.20, 'volatility': 0.10
            },
            'default_sharpe': results_default['sharpe_ratio'],
            'default_total_return': results_default['total_return'],
            'optimized_weights': best_weights,
            'optimized_sharpe': results_optimized['sharpe_ratio'],
            'optimized_total_return': results_optimized['total_return'],
            'sharpe_improvement': results_optimized['sharpe_ratio'] - results_default['sharpe_ratio'],
            'return_improvement': results_optimized['total_return'] - results_default['total_return'],
            'market_state': optimizer.market_state
        }
        
    except Exception as e:
        print(f"[ERROR] 回测失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    # 测试科创50
    result = run_backtest_for_index('000688.SH', '科创50')
    
    if result:
        print("\n" + "="*80)
        print("回测总结")
        print("="*80)
        print(f"指数: {result['index_name']} ({result['index_code']})")
        print(f"默认权重夏普比率: {result['default_sharpe']:.4f}")
        print(f"优化后夏普比率: {result['optimized_sharpe']:.4f}")
        print(f"夏普比率提升: {result['sharpe_improvement']:+.4f}")
        print(f"市场状态: {result['market_state']}")
