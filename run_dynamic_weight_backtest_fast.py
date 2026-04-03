#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
动态权重调整优化 - 快速回测脚本 (仅验证功能)
"""
import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_factor_scorer import MultiFactorScorer
from analysis.dynamic_weight_optimizer import DynamicWeightOptimizer
from analysis.backtester import Backtester

# 8个指数列表
INDEX_LIST = [
    ('000688.SH', '科创50'),
    ('399006.SZ', '创业板指'),
    ('000001.SH', '上证综指'),
    ('399300.SZ', '沪深300'),
    ('000905.SH', '中证500'),
    ('399102.SZ', '深证成指'),
    ('000016.SH', '上证50'),
    ('000852.SH', '中证1000'),
]

def quick_backtest(index_code, index_name, n_trials=20):  # 减少trials加快速度
    """快速回测单个指数"""
    print(f"\n{'='*70}")
    print(f"[OK] 回测指数: {index_name} ({index_code})")
    print('='*70)
    
    try:
        # 1. 加载数据
        analyzer = IndexAnalyzer(index_code, start_date='20230101')
        result = analyzer.analyze(include_ml=False)
        df = result
        
        # 2. 默认权重回测
        print("[OK] 默认权重回测...")
        scorer_def = MultiFactorScorer()
        df_def = scorer_def.calculate(df)
        bt = Backtester()
        results_def = bt.run(df_def, signal_column='final_signal')
        
        # 3. 优化权重（快速版，20 trials）
        print(f"[OK] 开始优化 (n_trials=20)...")
        optimizer = DynamicWeightOptimizer(n_trials=20)  # 设置n_trials=20
        best_weights = optimizer.optimize(df)
        
        # 4. 优化后回测
        print("[OK] 优化后权重回测...")
        scorer_opt = MultiFactorScorer(weights=best_weights)
        df_opt = scorer_opt.calculate(df)
        results_opt = bt.run(df_opt, signal_column='final_signal')
        
        # 5. 输出结果
        print(f"\n[CLEAR] 结果对比:")
        print(f"  默认夏普: {results_def['sharpe_ratio']:.4f} -> 优化夏普: {results_opt['sharpe_ratio']:.4f} "
              f"[{results_opt['sharpe_ratio'] - results_def['sharpe_ratio']:+.4f}]")
        print(f"  市场状态: {optimizer.market_state}")
        
        # 6. 权重分布
        print(f"\n[CLEAR] 最优权重分布:")
        for factor, weight in best_weights.items():
            print(f"  {factor:<10}: {weight*100:6.1f}%")
        
        return {
            'index': index_name,
            'default_sharpe': results_def['sharpe_ratio'],
            'optimized_sharpe': results_opt['sharpe_ratio'],
            'improvement': results_opt['sharpe_ratio'] - results_def['sharpe_ratio'],
            'weights': best_weights,
            'market_state': optimizer.market_state
        }
        
    except Exception as e:
        print(f"[ERROR] 回测失败: {str(e)[:100]}")
        return None

def run_all():
    """回测全部8个指数"""
    print("="*70)
    print("动态权重调整 - 快速回测 (8个指数, 20 trials/指数)")
    print("="*70)
    
    results = []
    for index_code, index_name in INDEX_LIST:
        result = quick_backtest(index_code, index_name, n_trials=20)
        if result:
            results.append(result)
    
    # 总结
    print("\n" + "="*70)
    print("SUMMARY - 动态权重优化效果")
    print("="*70)
    
    print(f"\n{'指数':<10} {'默认夏普':>8} {'优化夏普':>8} {'提升':>8} {'市场状态':<10}")
    print("-"*70)
    
    for r in results:
        print(f"{r['index']:<10} {r['default_sharpe']:>8.4f} {r['optimized_sharpe']:>8.4f} "
              f"{r['improvement']:>+8.4f} {r['market_state']:<10}")
    
    # 保存JSON结果
    import json
    import os
    output_file = os.path.join(r'E:\pycharm\stock-analysis', 'dynamic_weight_results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n[OK] 结果已保存到: {output_file}")

if __name__ == '__main__':
    run_all()
