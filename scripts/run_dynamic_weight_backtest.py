#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
动态权重调整优化 - 完整回测脚本
"""
import sys
import os
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_factor_scorer import MultiFactorScorer
from analysis.dynamic_weight_optimizer import DynamicWeightOptimizer
from analysis.backtester import Backtester
import pandas as pd
import json

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
        scorer_default = MultiFactorScorer()
        df_default = scorer_default.calculate(df.copy())
        
        default_weight = scorer_default.weights
        
        # 回测
        backtester = Backtester()
        result_default = backtester.run(df=df_default, signal_column='final_signal')
        metrics_default = result_default
        
        # 3. 优化权重
        print("\n步骤2: 优化多因子权重...")
        optimizer = DynamicWeightOptimizer(n_trials=50)
        best_weights = optimizer.optimize(df)
        
        # 4. 使用最优权重
        print("\n步骤3: 使用最优权重重新回测...")
        scorer_optimized = MultiFactorScorer(weights=best_weights)
        df_optimized = scorer_optimized.calculate(df.copy())
        
        result_optimized = backtester.run(df=df_optimized, signal_column='final_signal')
        metrics_optimized = result_optimized
        
        # 5. 市场状态分析
        market_state = optimizer.analyze_market_state(df)
        adaptive_weights = optimizer.get_adaptive_weights(market_state)
        
        # 6. 输出结果
        print("\n" + "="*80)
        print("回测结果对比")
        print("="*80)
        
        print(f"\n默认权重: {default_weight}")
        print(f"默认夏普比率: {metrics_default.get('sharpe_ratio', 0):.4f}")
        print(f"默认总收益: {metrics_default.get('total_return', 0)*100:.2f}%")
        
        print(f"\n最优权重: {best_weights}")
        print(f"最优夏普比率: {metrics_optimized.get('sharpe_ratio', 0):.4f}")
        print(f"最优总收益: {metrics_optimized.get('total_return', 0)*100:.2f}%")
        
        print(f"\n市场状态: {market_state}")
        print(f"自适应权重: {adaptive_weights}")
        
        return {
            'index_code': index_code,
            'index_name': index_name,
            'default_weights': default_weight,
            'best_weights': best_weights,
            'market_state': market_state,
            'adaptive_weights': adaptive_weights,
            'default_metrics': metrics_default,
            'optimized_metrics': metrics_optimized
        }
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """主函数"""
    print("="*80)
    print("动态权重调整优化 - 完整回测")
    print("="*80)
    
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
    
    results = []
    
    for idx_code, idx_name in indices:
        result = run_backtest_for_index(idx_code, idx_name)
        if result:
            results.append(result)
    
    # 输出汇总
    print("\n" + "="*80)
    print("回测汇总")
    print("="*80)
    
    for r in results:
        print(f"\n{r['index_name']} ({r['index_code']}):")
        print(f"  默认夏普: {r['default_metrics'].get('sharpe_ratio', 0):.4f}")
        print(f"  优化夏普: {r['optimized_metrics'].get('sharpe_ratio', 0):.4f}")
        print(f"  夏普提升: {r['optimized_metrics'].get('sharpe_ratio', 0) - r['default_metrics'].get('sharpe_ratio', 0):.4f}")
        print(f"  默认收益: {r['default_metrics'].get('total_return', 0)*100:.2f}%")
        print(f"  优化收益: {r['optimized_metrics'].get('total_return', 0)*100:.2f}%")
        print(f"  收益提升: {(r['optimized_metrics'].get('total_return', 0) - r['default_metrics'].get('total_return', 0))*100:.2f}%")
    
    # 保存结果
    with open('DYNAMIC_WEIGHT_BACKTEST_RESULTS.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n结果已保存到: DYNAMIC_WEIGHT_BACKTEST_RESULTS.json")

if __name__ == '__main__':
    try:
        main()
        print("\n[OK] 完成!")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
