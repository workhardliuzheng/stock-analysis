#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票分析系统 Skill - 测试脚本
"""
import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

def test_imports():
    """测试导入"""
    print("测试导入...")
    
    try:
        from analysis.index_analyzer import IndexAnalyzer
        print("  [OK] IndexAnalyzer")
    except Exception as e:
        print(f"  [ERROR] IndexAnalyzer: {e}")
        return False
    
    try:
        from analysis.multi_factor_scorer import MultiFactorScorer
        print("  [OK] MultiFactorScorer")
    except Exception as e:
        print(f"  [ERROR] MultiFactorScorer: {e}")
        return False
    
    try:
        from analysis.signal_threshold_optimizer import get_aggressive_lite_threshold_optimizer
        print("  [OK] SignalThresholdOptimizer")
    except Exception as e:
        print(f"  [ERROR] SignalThresholdOptimizer: {e}")
        return False
    
    try:
        from analysis.adaptive_fusion_optimizer import MetaLearner
        print("  [OK] MetaLearner")
    except Exception as e:
        print(f"  [ERROR] MetaLearner: {e}")
        return False
    
    try:
        from analysis.ml_predictor import MLPredictor
        print("  [OK] MLPredictor")
    except Exception as e:
        print(f"  [ERROR] MLPredictor: {e}")
        return False
    
    return True

def test_module():
    """测试模块功能"""
    print("\n测试模块功能...")
    
    try:
        from analysis.index_analyzer import IndexAnalyzer
        
        # 测试 IndexAnalyzer
        print("  测试 IndexAnalyzer...")
        analyzer = IndexAnalyzer('000688.SH', start_date='20230101')
        result = analyzer.analyze(include_ml=False)
        print(f"    [OK] 加载 {len(result)} 行数据")
        
        # 测试 MultiFactorScorer
        print("  测试 MultiFactorScorer...")
        scorer = MultiFactorScorer()
        df = scorer.calculate(result)
        print(f"    [OK] 多因子评分完成")
        
        # 测试 SignalThresholdOptimizer
        print("  测试 SignalThresholdOptimizer...")
        optimizer = get_aggressive_lite_threshold_optimizer()
        signal, _ = optimizer.generate_signal(55, 'uptrend')
        print(f"    [OK] 生成信号: {signal}")
        
        # 测试 MetaLearner
        print("  测试 MetaLearner...")
        df['ml_predicted_return'] = df['factor_score'].diff().fillna(0) / 10
        df['ml_signal'] = df['factor_signal']
        
        meta_learner = MetaLearner(market_state='oscillation')
        df = meta_learner.generate_fused_signal(df)
        print(f"    [OK] 融合信号完成")
        
        return True
        
    except Exception as e:
        print(f"  [ERROR] 出错: {e}")
        return False

def main():
    """主函数"""
    print("="*60)
    print("股票分析系统 Skill - 测试")
    print("="*60)
    
    # 1. 测试导入
    print("\n[1/2] 导入测试")
    if not test_imports():
        print("\n[ERROR] 导入测试失败")
        return False
    
    # 2. 测试功能
    print("\n[2/2] 功能测试")
    if not test_module():
        print("\n[ERROR] 功能测试失败")
        return False
    
    print("\n[OK] 所有测试通过!")
    print("="*60)
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
