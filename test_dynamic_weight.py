#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
动态权重调整优化 - 测试脚本
"""
import sys
import os
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.multi_factor_scorer import MultiFactorScorer
from analysis.dynamic_weight_optimizer import DynamicWeightOptimizer
from analysis.index_analyzer import IndexAnalyzer

def test_single_index():
    """测试单个指数"""
    print("=" * 80)
    print("动态权重调整优化 - 单指数测试")
    print("=" * 80)
    
    index_code = '000688.SH'  # 科创50
    print(f"\n测试指数: {index_code}")
    
    # 创建分析器
    analyzer = IndexAnalyzer(index_code, start_date='20230101')
    
    # 运行分析（只做多因子，不做ML）
    print("\n正在计算多因子评分...")
    result = analyzer.analyze(include_ml=False)
    
    if result is not None and len(result) > 0:
        df = result
        
        print(f"[OK] 分析完成")
        print(f"数据行数: {len(df)}")
        
        # 1. 使用默认权重
        print("\n" + "=" * 80)
        print("步骤1: 使用默认权重")
        print("=" * 80)
        
        scorer_default = MultiFactorScorer()
        df_default = scorer_default.calculate(df.copy())
        
        default_weight = scorer_default.weights
        print(f"默认权重: {default_weight}")
        
        # 2. 优化权重
        print("\n" + "=" * 80)
        print("步骤2: 优化多因子权重")
        print("=" * 80)
        
        optimizer = DynamicWeightOptimizer(n_trials=30)  # 减少试验次数加快测试
        best_weights = optimizer.optimize(df)
        
        # 3. 使用最优权重
        print("\n" + "=" * 80)
        print("步骤3: 使用最优权重重新计算")
        print("=" * 80)
        
        scorer_optimized = MultiFactorScorer(weights=best_weights)
        df_optimized = scorer_optimized.calculate(df.copy())
        
        print(f"最优权重: {best_weights}")
        
        # 4. 比较评分
        if 'factor_score' in df_default.columns and 'factor_score' in df_optimized.columns:
            print("\n评分对比:")
            print(f"  默认权重平均评分: {df_default['factor_score'].mean():.2f}")
            print(f"  优化权重平均评分: {df_optimized['factor_score'].mean():.2f}")
        
        # 5. 市场状态分析
        print("\n" + "=" * 80)
        print("步骤4: 市场状态分析")
        print("=" * 80)
        
        market_state = optimizer.analyze_market_state(df)
        print(f"当前市场状态: {market_state}")
        
        adaptive_weights = optimizer.get_adaptive_weights(market_state)
        print(f"自适应权重: {adaptive_weights}")
        
        return {
            'default_weights': default_weight,
            'best_weights': best_weights,
            'market_state': market_state,
            'adaptive_weights': adaptive_weights
        }
    else:
        print("[ERROR] 分析失败")
        return None

if __name__ == '__main__':
    try:
        results = test_single_index()
        
        if results:
            print("\n" + "=" * 80)
            print("测试完成!")
            print("=" * 80)
            print(f"\n权重对比:")
            print(f"  默认: {results['default_weights']}")
            print(f"  最优: {results['best_weights']}")
            print(f"  自适应: {results['adaptive_weights']}")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
