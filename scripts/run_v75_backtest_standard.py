#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V7-5标准回测验证脚本

每次优化后必须执行此脚本，确保回测结果可比性！

功能:
1. 固定指数配置：科创50/创业板指/上证综指/中证500/中证1000
2. 固定权重分配：每个指数20%
3. 固定时间范围：20230101~2026-04-06 (5年)
4. 固定策略：多因子 vs V7-5融合

输出:
- records/v75_backtest_YYYYMMDD.txt
- 更新 V7-5_BACKTEST_LOG.md
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
from analysis.adaptive_fusion_optimizer import MetaLearner, AdaptiveFusionOptimizer
import pandas as pd


def print_line(char='=', length=80):
    """打印分割线"""
    print(char * length)


def main():
    """V7-5标准回测"""
    print_line()
    print("V7-5 标准回测验证")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_line()
    
    # 固定配置
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
    
    # 1. 加载数据
    print("[步骤1] 加载指数数据...")
    index_data = {}
    
    for code, info in INDEX_PORTFOLIO.items():
        try:
            print(f"  正在加载 {info['name']:>8} ({code})...")
            
            analyzer = IndexAnalyzer(code, start_date='20210101')
            analyzer.analyze(include_ml=True, auto_tune=False)
            
            df = analyzer.data
            
            # 检查必要列
            required_cols = ['factor_score', 'factor_signal', 'ml_predicted_return', 
                           'ml_signal', 'ml_probability', 'pct_chg']
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
    
    # 2. 计算多因子策略收益
    print("\n[步骤2] 计算多因子策略收益...")
    for code, info in index_data.items():
        try:
            df = info['data'].copy()
            df['signal'] = df['factor_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)
            
            # 简化回测
            initial_capital = 100000
            capital = initial_capital
            positions = 0
            
            for i in range(1, len(df)):
                signal = df.iloc[i]['signal']
                pct_chg = df.iloc[i]['pct_chg'] / 100.0
                
                if signal == 1 and positions == 0:  # 买入
                    positions = capital
                elif signal == -1 and positions > 0:  # 卖出
                    capital = positions * (1 + pct_chg)
                    positions = 0
            
            if positions > 0:
                capital = positions * (1 + df.iloc[-1]['pct_chg'] / 100.0)
            
            info['factor_return'] = (capital - initial_capital) / initial_capital * 100
            print(f"  {info['name']:>8}: {info['factor_return']:>+7.2f}%")
            
        except Exception as e:
            print(f"  [ERROR] {info['name']} 计算失败: {e}")
            info['factor_return'] = 0.0
    
    # 3. 计算V7-5融合策略收益
    print("\n[步骤3] 计算V7-5融合策略收益...")
    for code, info in index_data.items():
        try:
            df = info['data'].copy()
            
            # 使用V7-5自适应融合
            optimizer = AdaptiveFusionOptimizer()
            weights = {
                'factor_score': 0.7358,
                'factor_signal': 0.0394,
                'ml_return': 0.1679,
                'ml_signal': 0.0568
            }
            
            # 计算融合评分
            df['fused_score'] = (
                weights['factor_score'] * df['factor_score'] +
                weights['factor_signal'] * df['factor_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0) +
                weights['ml_return'] * df['ml_predicted_return'] * 100 +
                weights['ml_signal'] * df['ml_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)
            )
            
            # 添加信号
            buy_threshold = 0.5
            sell_threshold = -0.5
            df['v75_signal'] = df['fused_score'].apply(
                lambda x: 'BUY' if x > buy_threshold else ('SELL' if x < sell_threshold else 'HOLD')
            )
            
            # 简化回测
            initial_capital = 100000
            capital = initial_capital
            positions = 0
            
            for i in range(1, len(df)):
                signal = df.iloc[i]['v75_signal']
                pct_chg = df.iloc[i]['pct_chg'] / 100.0
                
                if signal == 'BUY' and positions == 0:
                    positions = capital
                elif signal == 'SELL' and positions > 0:
                    capital = positions * (1 + pct_chg)
                    positions = 0
            
            if positions > 0:
                capital = positions * (1 + df.iloc[-1]['pct_chg'] / 100.0)
            
            info['v75_return'] = (capital - initial_capital) / initial_capital * 100
            print(f"  {info['name']:>8}: {info['v75_return']:>+7.2f}%")
            
        except Exception as e:
            print(f"  [ERROR] {info['name']} 计算失败: {e}")
            info['v75_return'] = 0.0
    
    # 4. 计算组合收益
    print("\n[步骤4] 计算组合收益...")
    
    total_factor_return = sum(info['factor_return'] * info['weight'] for info in index_data.values())
    total_v75_return = sum(info['v75_return'] * info['weight'] for info in index_data.values())
    total提升 = total_v75_return - total_factor_return
    
    print(f"\n[组合结果]")
    print(f"原始多因子策略: {total_factor_return:+7.2f}%")
    print(f"V7-5融合策略:   {total_v75_return:+7.2f}%")
    print(f"收益提升:       {total提升:+7.2f}%")
    
    # 5. 打印详细指数收益
    print(f"\n[各指数收益]")
    print_line('-', 40)
    print(f"{'指数':<10} {'多因子':>8} {'V7-5':>8} {'提升':>8}")
    print_line('-', 40)
    
    for code, info in index_data.items():
        improvement = info['v75_return'] - info['factor_return']
        print(f"{info['name']:<10} {info['factor_return']:>8.2f}% {info['v75_return']:>8.2f}% {improvement:>8.2f}%")
    
    print_line('-', 40)
    
    # 6. 保存结果
    print("\n[步骤5] 保存结果...")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result_file = f'records/v75_backtest_{timestamp}.txt'
    
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write("V7-5 标准回测验证结果\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"[组合结果]\n")
        f.write(f"原始多因子策略: {total_factor_return:+.2f}%\n")
        f.write(f"V7-5融合策略:   {total_v75_return:+.2f}%\n")
        f.write(f"收益提升:       {total提升:+.2f}%\n\n")
        f.write(f"[各指数收益]\n")
        for code, info in index_data.items():
            improvement = info['v75_return'] - info['factor_return']
            f.write(f"{info['name']}: 多因子{info['factor_return']:.2f}%, V7-5{info['v75_return']:.2f}%, 提升{improvement:.2f}%\n")
    
    print(f"[OK] 结果已保存: {result_file}")
    
    # 7. 判断优化效果
    print("\n[优化效果判断]")
    
    if total提升 >= 10:
        print(f"[✅ 有效] V7-5策略提升 {total提升:.2f}% >= 10%")
        print("[✅ 建议] 更新文档并提交")
    elif total提升 >= 0:
        print(f"[⚠️  一般] V7-5策略提升 {total提升:.2f}% < 10%")
        print("[❌ 建议] 谨慎提交，确保无其他问题")
    else:
        print(f"[❌ 无效] V7-5策略下降 {abs(total提升):.2f}%")
        print("[❌ 建议] 回滚代码!")
    
    print()
    print_line()
    print("[OK] V7-5标准回测完成!")
    print_line()
    
    return {
        'total_factor_return': total_factor_return,
        'total_v75_return': total_v75_return,
        'total_improvement': total提升,
        'index_results': index_data
    }


if __name__ == '__main__':
    main()
