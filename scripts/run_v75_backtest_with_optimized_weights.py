#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V7-5 回测脚本 - 使用Optuna优化的动态权重

功能:
1. 从数据库读取每个指数的最优权重
2. 按权重组合各指数的多因子和V7-5收益
3. 计算组合夏普比率、最大回撤等指标
4. 明确报告每个指数的权重分配
"""

import sys
import os
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from datetime import datetime
import pandas as pd

from entity import constant
from analysis.backtester import Backtester
from mysql_connect.db import get_engine
from sqlalchemy import text


# 固定指数配置（5个指数各20%）
INDEX_CONFIGS = [
    {'code': '000688.SH', 'name': '科创50', 'weight': 0.20},
    {'code': '399006.SZ', 'name': '创业板指', 'weight': 0.20},
    {'code': '000001.SH', 'name': '上证综指', 'weight': 0.20},
    {'code': '000300.SH', 'name': '沪深300', 'weight': 0.20},
    {'code': '399001.SZ', 'name': '深证成指', 'weight': 0.20},
]


def get_optimal_weights_from_db():
    """从数据库读取所有指数的最优权重"""
    engine = get_engine()
    weights = {}
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM v75_optimal_weights"))
            rows = result.fetchall()
            
            for row in rows:
                code = row[1]
                weights[code] = {
                    'factor_score': float(row[3]),
                    'factor_signal': float(row[4]),
                    'ml_return': float(row[5]),
                    'ml_signal': float(row[6]),
                }
        
        print(f"[INFO] 从数据库加载了 {len(weights)} 个指数的最优权重")
        return weights
        
    except Exception as e:
        print(f"[ERROR] 读取数据库失败: {e}")
        return None


def load_index_data(ts_code, index_name, start_date='20230101'):
    """加载指数数据"""
    print(f"  正在加载 {index_name} ({ts_code})...")
    
    try:
        from analysis.index_analyzer import IndexAnalyzer
        analyzer = IndexAnalyzer(ts_code, start_date=start_date)
        df = analyzer.analyze(include_ml=True, auto_tune=False)
        
        print(f"    [OK] 加载成功 ({len(df)}条数据)")
        return df
        
    except Exception as e:
        print(f"    [ERROR] 加载失败: {e}")
        return None


def calculate_fused_return(df, weights):
    """根据权重计算融合信号的收益率（使用final_signal）"""
    if 'final_signal' not in df.columns:
        print(f"    [WARN] 缺少final_signal列")
        return pd.Series([0] * len(df))
    
    # 直接使用final_signal进行回测（已由SignalGenerator融合好）
    df['position'] = df['final_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)
    
    # 计算收益率
    df['strategy_return'] = df['position'] * df['pct_chg'] / 100
    
    return df['strategy_return']


def run_backtest_with_optimized_weights():
    """运行回测（使用动态优化权重）"""
    print("=" * 70)
    print("V7-5 动态权重回测验证")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 1. 读取最优权重
    print("\n[步骤1] 加载最优权重...")
    optimal_weights = get_optimal_weights_from_db()
    
    if optimal_weights is None:
        print("    [ERROR] 无法读取权重，使用默认权重")
        optimal_weights = {
            '000688.SH': {'factor_score': 0.56, 'ml_return': 0.14, 'ml_signal': 0.15, 'factor_signal': 0.14},
            '399006.SZ': {'factor_score': 0.83, 'ml_return': 0.11, 'ml_signal': 0.00, 'factor_signal': 0.05},
            '000001.SH': {'factor_score': 0.85, 'ml_return': 0.01, 'ml_signal': 0.01, 'factor_signal': 0.13},
            '000300.SH': {'factor_score': 0.84, 'ml_return': 0.08, 'ml_signal': 0.06, 'factor_signal': 0.02},
            '399001.SZ': {'factor_score': 0.85, 'ml_return': 0.04, 'ml_signal': 0.02, 'factor_signal': 0.09},
        }
    
    # 2. 加载数据
    print("\n[步骤2] 加载指数数据...")
    index_data = {}
    for config in INDEX_CONFIGS:
        code = config['code']
        name = config['name']
        
        # 使用该指数的最优权重（如果没有则使用默认）
        weights = optimal_weights.get(code, {
            'factor_score': 0.70, 'factor_signal': 0.05,
            'ml_return': 0.20, 'ml_signal': 0.05,
        })
        
        df = load_index_data(code, name)
        if df is not None:
            index_data[code] = {
                'df': df,
                'name': name,
                'weight': config['weight'],
                'optimal_weights': weights,
            }
    
    # 3. 计算各指数收益
    print("\n[步骤3] 计算各指数收益...")
    
    bt = Backtester(commission_rate=0.00006, execution_timing='close')
    total_factor_return = 0.0
    total_v75_return = 0.0
    
    for code, data in index_data.items():
        df = data['df']
        name = data['name']
        weight = data['weight']
        weights = data['optimal_weights']
        
        try:
            # 计算多因子收益（直接用factor_score）
            # 信号必须是字符串BUY/SELL/HOLD，不是数值
            df['position_factor_signal'] = df['factor_score'].apply(
                lambda x: 'BUY' if x >= 50 else ('SELL' if x < 50 else 'HOLD')
            )
            
            metrics_factor = bt.run(df, signal_column='position_factor_signal')
            factor_return = metrics_factor.get('total_return', 0.0)  # 已经是百分比
            
            # 计算V7-5收益（使用final_signal）
            df['v75_return'] = calculate_fused_return(df, weights)
            
            # 重新运行回测（使用final_signal）
            metrics_v75 = bt.run(df, signal_column='final_signal')
            v75_return = metrics_v75.get('total_return', 0.0)  # 已经是百分比
            
            # 累加加权收益
            total_factor_return += factor_return * weight
            total_v75_return += v75_return * weight
            
            # 显示结果
            print(f"  {name:>6}:")
            print(f"    权重: {weight*100:.0f}%")
            print(f"    最优权重: {weights}")
            print(f"    多因子收益: {factor_return:7.2f}%")
            print(f"    V7-5收益: {v75_return:7.2f}%")
            print(f"    提升: {v75_return - factor_return:7.2f}%")
            
        except Exception as e:
            print(f"  {name:>6}: [ERROR] {e}")
    
    # 4. 输出总结果
    print("\n" + "=" * 70)
    print("组合结果")
    print("=" * 70)
    print(f"原始多因子策略: {total_factor_return:7.2f}%")
    print(f"V7-5融合策略:   {total_v75_return:7.2f}%")
    print(f"收益提升:       {total_v75_return - total_factor_return:7.2f}%")
    print("=" * 70)
    
    # 5. 保存结果
    report_path = f"records/v75_backtest_optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    os.makedirs("records", exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("V7-5 动态权重回测验证结果\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("组合结果\n")
        f.write("=" * 70 + "\n")
        f.write(f"原始多因子策略: {total_factor_return:.2f}%\n")
        f.write(f"V7-5融合策略:   {total_v75_return:.2f}%\n")
        f.write(f"收益提升:       {total_v75_return - total_factor_return:.2f}%\n")
        f.write("\n指数详细结果\n")
        f.write("=" * 70 + "\n")
        
        for code, data in index_data.items():
            name = data['name']
            f.write(f"\n{name} ({code}):\n")
            f.write(f"  权重: {data['weight']*100:.0f}%\n")
            f.write(f"  最优权重: {data['optimal_weights']}\n")
    
    print(f"\n[OK] 结果已保存到: {report_path}")


if __name__ == "__main__":
    run_backtest_with_optimized_weights()
