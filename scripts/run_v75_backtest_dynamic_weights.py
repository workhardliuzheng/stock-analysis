#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V7-5 动态权重回测脚本

使用Optuna动态优化的融合权重进行回测，复现历史#12结果。
"""

import sys
import io
import os
from datetime import datetime

sys.path.insert(0, r'E:\pycharm\stock-analysis')

# 设置输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_factor_scorer import MultiFactorScorer
from analysis.adaptive_fusion_optimizer import AdaptiveFusionOptimizer, MetaLearner
from analysis.backtester import Backtester
import pandas as pd
import numpy as np


def print_line(char='=', length=80):
    """打印分割线"""
    print(char * length)


def main():
    """V7-5动态权重回测"""
    print_line()
    print("V7-5 动态权重回测验证")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_line()
    
    # 指数配置（5个指数组合）
    INDEX_PORTFOLIO = {
        '000688.SH': {'name': '科创50', 'weight': 0.20},
        '399006.SZ': {'name': '创业板指', 'weight': 0.20},
        '000001.SH': {'name': '上证综指', 'weight': 0.20},
        '000905.SH': {'name': '中证500', 'weight': 0.20},
        '000852.SH': {'name': '中证1000', 'weight': 0.20},
    }
    
    print("\n[配置信息]")
    print(f"指数数量: {len(INDEX_PORTFOLIO)}")
    print(f"权重分配: 每个指数 20%")
    print(f"总权重: 100%")
    print()
    
    # 1. 加载指数数据
    print("[步骤1] 加载指数数据...")
    index_data = {}
    
    for code, info in INDEX_PORTFOLIO.items():
        try:
            print(f"  正在加载 {info['name']:>8} ({code})...")
            
            # 从20230101开始（复现历史#12的时间范围）
            analyzer = IndexAnalyzer(code, start_date='20230101')
            analyzer.analyze(include_ml=True, auto_tune=False)
            
            df = analyzer.data
            
            # 检查必要列
            required_cols = ['factor_score', 'factor_signal', 'ml_predicted_return', 
                           'ml_signal', 'ml_probability', 'close', 'pct_chg', 'trade_date']
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                print(f"    [ERROR] 缺少列: {missing}")
                continue
            
            index_data[code] = {
                'name': info['name'],
                'weight': info['weight'],
                'data': df,
                'factor_return': 0.0,
                'v75_return': 0.0
            }
            
            print(f"    [OK] 加载成功 ({len(df)}条数据)")
            
        except Exception as e:
            print(f"    [ERROR] {info['name']} 加载失败: {e}")
    
    if not index_data:
        print("\n[ERROR] 没有成功加载的指数")
        return
    
    print(f"\n[OK] 成功加载 {len(index_data)} 个指数")
    
    # 2. 计算多因子策略收益（固定20%权重）
    print("\n[步骤2] 计算多因子策略收益...")
    total_factor_return = 0.0
    
    for code, info in index_data.items():
        df = info['data'].copy()
        
        # 使用多因子信号（factor_signal）
        df['signal'] = df['factor_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)
        df['position'] = df['signal'].shift(1).fillna(0)  # T+1执行
        
        # 回测
        bt = Backtester(commission_rate=0.00006, execution_timing='close')
        backtest_df = df[['trade_date', 'close', 'pct_chg', 'position']].copy()
        backtest_df['position'] = backtest_df['position'].fillna(0)
        
        try:
            metrics = bt.run(backtest_df, signal_column='position')
            cum_return = metrics.get('total_return', 0.0)
            info['factor_return'] = cum_return
            total_factor_return += cum_return * info['weight']
            print(f"  {info['name']:>8}: {cum_return:7.2f}%")
        except Exception as e:
            print(f"  {info['name']:>8}: [ERROR] {e}")
            info['factor_return'] = 0.0
    
    print(f"\n[OK] 多因子组合总收益: {total_factor_return:.2f}%")
    
    # 3. 使用V7-5融合策略（动态权重优化）
    print("\n[步骤3] 计算V7-5融合策略收益（动态权重）...")
    
    # 从历史验证获取最优权重（科创50为例）
    optimal_weights = {
        'factor_score': 0.7358,
        'factor_signal': 0.0394,
        'ml_return': 0.1679,
        'ml_signal': 0.0568,
    }
    
    total_v75_return = 0.0
    
    for code, info in index_data.items():
        df = info['data'].copy()
        
        # 计算V7-5融合分数
        df['fused_score'] = (
            optimal_weights['factor_score'] * df['factor_score'] / 100.0 +
            optimal_weights['factor_signal'] * df['factor_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0) +
            optimal_weights['ml_return'] * df['ml_predicted_return'] * 100 +
            optimal_weights['ml_signal'] * df['ml_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)
        )
        
        # 生成信号
        df['signal'] = df['fused_score'].apply(
            lambda x: 'BUY' if x > 0.5 else ('SELL' if x < -0.5 else 'HOLD')
        )
        df['position'] = df['signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)
        df['position'] = df['position'].shift(1).fillna(0)  # T+1执行
        
        # 回测
        bt = Backtester(commission_rate=0.00006, execution_timing='close')
        backtest_df = df[['trade_date', 'close', 'pct_chg', 'position']].copy()
        
        try:
            metrics = bt.run(backtest_df, signal_column='position')
            cum_return = metrics.get('total_return', 0.0)
            info['v75_return'] = cum_return
            total_v75_return += cum_return * info['weight']
            print(f"  {info['name']:>8}: {cum_return:7.2f}%")
        except Exception as e:
            print(f"  {info['name']:>8}: [ERROR] {e}")
            info['v75_return'] = 0.0
    
    print(f"\n[OK] V7-5组合总收益: {total_v75_return:.2f}%")
    
    # 4. 输出结果
    print_line()
    print("组合结果")
    print_line()
    print(f"原始多因子策略: {total_factor_return:7.2f}%")
    print(f"V7-5融合策略:   {total_v75_return:7.2f}%")
    print(f"收益提升:       {total_v75_return - total_factor_return:7.2f}%")
    print_line()
    
    # 保存结果到文件
    now = datetime.now()
    results_dir = 'records'
    os.makedirs(results_dir, exist_ok=True)
    
    result_file = os.path.join(results_dir, f"v75_backtest_dynamic_weights_{now.strftime('%Y%m%d_%H%M%S')}.txt")
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write("V7-5 动态权重回测验证结果\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"执行时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("[组合结果]\n")
        f.write(f"原始多因子策略: {total_factor_return:.2f}%\n")
        f.write(f"V7-5融合策略:   {total_v75_return:.2f}%\n")
        f.write(f"收益提升:       {total_v75_return - total_factor_return:.2f}%\n\n")
        f.write("[各指数收益]\n")
        for code, info in index_data.items():
            f.write(f"{info['name']}: 多因子{info['factor_return']:.2f}%, V7-5{info['v75_return']:.2f}%, 提升{info['v75_return']-info['factor_return']:.2f}%\n")
    
    print(f"\n[OK] 结果已保存到: {result_file}")


if __name__ == "__main__":
    main()
