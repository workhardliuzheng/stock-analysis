#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V7-4 信号阈值优化测试脚本

测试不同阈值策略的信号分布效果
"""
import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_factor_scorer import MultiFactorScorer
from analysis.signal_threshold_optimizer import (
    SignalThresholdOptimizer,
    get_aggressive_lite_threshold_optimizer,
    get_aggressive_threshold_optimizer,
    get_dynamic_threshold_optimizer
)
import pandas as pd

def test_original_signal(index_code='000688.SH'):
    """测试原始信号"""
    print("="*60)
    print("原始信号 (MultiFactorScorer)")
    print("="*60)
    
    analyzer = IndexAnalyzer(index_code, start_date='20230101')
    result = analyzer.analyze(include_ml=False)
    
    if result is None or len(result) == 0:
        print("[ERROR] 没有数据")
        return None
    
    # 统计
    signals = result['final_signal'].value_counts()
    signals_pct = signals / len(result) * 100
    
    print(f"\n信号分布:")
    for signal, count in signals.items():
        print(f"  {signal}: {count} ({signals_pct[signal]:.1f}%)")
    
    # factor_score统计
    scores = result['factor_score']
    print(f"\nfactor_score统计:")
    print(f"  最小值: {scores.min():.2f}")
    print(f"  最大值: {scores.max():.2f}")
    print(f"  平均值: {scores.mean():.2f}")
    
    return {'signals': dict(signals), 'scores': {'min': scores.min(), 'max': scores.max(), 'mean': scores.mean()}}


def test_optimized_signal(optimizer, index_code='000688.SH'):
    """测试优化后信号"""
    print(f"\n{'='*60}")
    print(f"优化信号 ({optimizer.strategy})")
    print('='*60)
    
    analyzer = IndexAnalyzer(index_code, start_date='20230101')
    result = analyzer.analyze(include_ml=False)
    
    if result is None or len(result) == 0:
        print("[ERROR] 没有数据")
        return None
    
    # 计算多因子评分
    scorer = MultiFactorScorer()
    df = scorer.calculate(result)
    
    # 使用优化器重新生成信号
    new_signals = []
    new_confidences = []
    
    for i in range(len(df)):
        row = df.iloc[i]
        score = row['factor_score']
        trend_state = row['trend_state']
        volatility = row.get('percentile_20', 1.5)  # 用历史百分位作为波动率代理
        
        signal, confidence = optimizer.generate_signal(score, trend_state, volatility=volatility)
        new_signals.append(signal)
        new_confidences.append(confidence)
    
    df['v74_signal'] = new_signals
    df['v74_confidence'] = new_confidences
    
    # 统计
    signals = df['v74_signal'].value_counts()
    signals_pct = signals / len(df) * 100
    
    print(f"\n信号分布:")
    for signal, count in signals.items():
        print(f"  {signal}: {count} ({signals_pct[signal]:.1f}%)")
    
    # factor_score统计
    scores = df['factor_score']
    print(f"\nfactor_score统计:")
    print(f"  最小值: {scores.min():.2f}")
    print(f"  最大值: {scores.max():.2f}")
    print(f"  平均值: {scores.mean():.2f}")
    
    return {'signals': dict(signals), 'scores': {'min': scores.min(), 'max': scores.max(), 'mean': scores.mean()}}


def compare_results(original, optimized):
    """对比结果"""
    print(f"\n{'='*60}")
    print("对比结果")
    print('='*60)
    
    if not original or not optimized:
        print("[ERROR] 无法对比")
        return
    
    # 信号对比
    print(f"\n信号分布对比:")
    print(f"  指标              默认值    优化值    对比")
    
    for signal in ['BUY', 'SELL', 'HOLD']:
        orig_count = original['signals'].get(signal, 0)
        opt_count = optimized['signals'].get(signal, 0)
        
        if orig_count > 0:
            change = (opt_count - orig_count) / orig_count * 100
        else:
            change = 100 if opt_count > 0 else 0
        
        print(f"  {signal:<8}: {orig_count:8} -> {opt_count:8} ({change:+.1f}%)")
    
    # 总体对比
    print(f"\n信号频率对比:")
    orig_buy_sell = original['signals'].get('BUY', 0) + original['signals'].get('SELL', 0)
    opt_buy_sell = optimized['signals'].get('BUY', 0) + optimized['signals'].get('SELL', 0)
    
    if orig_buy_sell > 0:
        improvement = (opt_buy_sell - orig_buy_sell) / orig_buy_sell * 100
    else:
        improvement = 100 if opt_buy_sell > 0 else 0
    
    print(f"  HOLD: {original['signals'].get('HOLD', 0):8} -> {optimized['signals'].get('HOLD', 0):8}")
    print(f"  BUY+SELL: {orig_buy_sell:8} -> {opt_buy_sell:8} ({improvement:+.1f}%)")
    
    # 评分范围对比
    print(f"\n评分范围对比:")
    print(f"  默认: {original['scores']['min']:5.2f} - {original['scores']['max']:5.2f} ( avg: {original['scores']['mean']:.2f} )")
    print(f"  优化: {optimized['scores']['min']:5.2f} - {optimized['scores']['max']:5.2f} ( avg: {optimized['scores']['mean']:.2f} )")


def main():
    """主函数"""
    print("="*60)
    print("V7-4 信号阈值优化测试")
    print("="*60)
    
    index_code = '000688.SH'
    index_name = '科创50'
    
    print(f"\n测试指数: {index_name} ({index_code})")
    
    # 1. 测试原始信号
    original = test_original_signal(index_code)
    
    # 2. 测试优化信号 (不同策略)
    strategies = [
        get_aggressive_lite_threshold_optimizer(),
        get_aggressive_threshold_optimizer()
    ]
    
    for optimizer in strategies:
        optimized = test_optimized_signal(optimizer, index_code)
        compare_results(original, optimized)


if __name__ == '__main__':
    main()
