#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V7-5回测可视化（含买卖点标记）

功能:
1. 对科创50进行5年回测
2. 生成一张图展示：
   - 指数原始走势（基准）
   - 多因子策略
   - ML策略
   - 混合策略（V7-5）
3. 标记所有买入（红色三角）和卖出（绿色倒三角）信号

执行:
    python scripts/visualize_backtest_with_trades.py
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, r'E:\pycharm\stock-analysis')

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

from analysis.index_analyzer import IndexAnalyzer
from analysis.backtester import Backtester
from entity import constant


def main():
    """主函数"""
    print("=" * 60)
    print("[OK] 开始V7-5回测可视化（含买卖点）")
    print("=" * 60)
    
    # 指数配置
    ts_code = '000688.SH'  # 科创50
    index_name = '科创50'
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365)  # 5年
    
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')
    
    print(f"[OK] 指数: {index_name} ({ts_code})")
    print(f"[OK] 时间范围: {start_date_str} ~ {end_date_str}")
    print()
    
    # 1. 获取数据
    print("[步骤1] 获取指数数据...")
    analyzer = IndexAnalyzer(ts_code)
    analyzer.analyze(include_ml=True, auto_tune=False)
    data = analyzer.data
    
    # 过滤时间范围
    if 'trade_date' in data.columns:
        data['trade_date_int'] = pd.to_numeric(data['trade_date'], errors='coerce')
        start_date_int = int(start_date_str.replace('-', ''))
        data = data[data['trade_date_int'] >= start_date_int]
        data = data.drop(columns=['trade_date_int'])
    
    if len(data) < 100:
        print(f"[ERROR] 数据不足: {len(data)}条")
        return
    
    print(f"[OK] 数据加载完成: {len(data)}条")
    print()
    
    # 2. 运行回测
    print("[步骤2] 运行回测...")
    bt = Backtester(
        initial_capital=100000,
        commission_rate=0.00006,
        execution_timing='close'
    )
    
    results = {}
    
    # 多因子策略
    if 'factor_signal' in data.columns:
        results['multi_factor'] = bt.run(data, 'factor_signal')
        print(f"[OK] 多因子策略: {results['multi_factor'].get('total_return', 0):+.2f}%")
    
    # ML策略
    if 'ml_signal' in data.columns:
        results['ml'] = bt.run(data, 'ml_signal')
        print(f"[OK] ML策略: {results['ml'].get('total_return', 0):+.2f}%")
    
    # 混合策略 (V7-5)
    if 'final_signal' in data.columns:
        results['combined'] = bt.run(data, 'final_signal')
        print(f"[OK] 混合策略(V7-5): {results['combined'].get('total_return', 0):+.2f}%")
        
        # 打印交易明细
        trades = results['combined'].get('trades', [])
        print(f"[OK] 交易次数: {len(trades)}")
        if trades:
            print("[OK] 前5笔交易:")
            for trade in trades[:5]:
                print(f"  {trade.get('type', 'UNKNOWN')}: {trade.get('entry_date', 'N/A')} -> {trade.get('exit_date', 'N/A')}")
    else:
        print("[ERROR] 没有final_signal列")
        return
    
    # 买入持有基准
    buy_hold_values = []
    cumulative_return = 1.0
    for i, pct in enumerate(data['pct_chg']):
        cumulative_return *= (1 + pct / 100.0)
        buy_hold_values.append(100000 * cumulative_return)
    
    results['buy_and_hold'] = {
        'initial_value': 100000,
        'final_value': buy_hold_values[-1] if buy_hold_values else 100000,
        'portfolio_values': buy_hold_values,
        'trade_dates': data['trade_date'].tolist(),
        'trades': []
    }
    print()
    
    # 3. 绘制图表
    print("[步骤3] 绘制图表...")
    generate_plot(index_name, ts_code, start_date_str, end_date_str, data, results)
    
    print()
    print("=" * 60)
    print("[OK] 回测可视化完成!")
    print("=" * 60)


def generate_plot(index_name: str, ts_code: str, 
                  start_date: str, end_date: str,
                  data: pd.DataFrame, 
                  results: dict):
    """生成回测对比图"""
    
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 创建画布
    fig, ax = plt.subplots(figsize=(16, 10))
    
    # 提取日期
    dates = pd.to_datetime([str(d) for d in results['buy_and_hold']['trade_dates']])
    
    # 绘制买入持有基准
    ax.plot(dates, results['buy_and_hold']['portfolio_values'], 
            label='买入持有基准', linestyle='--', linewidth=2, alpha=0.7, color='gray')
    
    # 绘制各策略
    colors = {
        'multi_factor': '#1f77b4',  # 蓝色
        'ml': '#ff7f0e',            # 橙色
        'combined': '#2ca02c',      # 绿色 (V7-5)
    }
    
    strategies = {
        'multi_factor': '多因子策略',
        'ml': 'ML策略',
        'combined': '混合策略 (V7-5)',
    }
    
    for key, name in strategies.items():
        if key in results and 'portfolio_values' in results[key]:
            values = results[key]['portfolio_values']
            final_return = (values[-1] / values[0] - 1) * 100
            ax.plot(dates, values, 
                   label=f'{name} ({final_return:+.1f}%)', 
                   linewidth=2.5, alpha=0.95, color=colors[key])
    
    # 添加买卖点标记
    print("[OK] 添加买卖点标记...")
    
    if 'combined' in results and 'trades' in results['combined']:
        buy_dates = []
        sell_dates = []
        buy_values = []
        sell_values = []
        
        for trade in results['combined']['trades']:
            # 买入点
            if 'entry_date' in trade:
                try:
                    date = pd.to_datetime(str(trade['entry_date']))
                    if len(dates) > 0 and date >= dates.iloc[0] and date <= dates.iloc[-1]:
                        buy_dates.append(date)
                        pos_idx = max(0, min(len(dates)-1, sum(dates <= date) - 1))
                        buy_values.append(results['combined']['portfolio_values'][pos_idx])
                        print(f"  买入: {trade['entry_date']} -> {trade.get('entry_price', 'N/A')}")
                except Exception as e:
                    print(f"  [ERROR] 买入点解析失败: {e}")
            
            # 卖出点
            if 'exit_date' in trade:
                try:
                    date = pd.to_datetime(str(trade['exit_date']))
                    if len(dates) > 0 and date >= dates.iloc[0] and date <= dates.iloc[-1]:
                        sell_dates.append(date)
                        pos_idx = max(0, min(len(dates)-1, sum(dates <= date) - 1))
                        sell_values.append(results['combined']['portfolio_values'][pos_idx])
                        print(f"  卖出: {trade['exit_date']} -> {trade.get('exit_price', 'N/A')}")
                except Exception as e:
                    print(f"  [ERROR] 卖出点解析失败: {e}")
        
        if buy_dates:
            ax.scatter(buy_dates, buy_values, c='red', s=150, marker='^', 
                      label=f'买入信号 ({len(buy_dates)})', zorder=6, edgecolors='darkred', linewidths=1.5)
        if sell_dates:
            ax.scatter(sell_dates, sell_values, c='green', s=150, marker='v', 
                      label=f'卖出信号 ({len(sell_dates)})', zorder=6, edgecolors='darkgreen', linewidths=1.5)
    
    # 格式化
    ax.set_title(f'{index_name} ({ts_code}) V7-5回测结果 ({start_date} ~ {end_date})\n'
                '包含买卖点标记', 
                fontsize=16, fontweight='bold', pad=20)
    ax.set_ylabel('组合价值 (元)', fontsize=14)
    ax.set_xlabel('日期', fontsize=14)
    ax.legend(loc='best', fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis='both', labelsize=12)
    ax.tick_params(axis='x', rotation=45)
    
    # 格式化x轴日期
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    
    # 添加绩效指标文本框
    metrics_dict = {}
    for key, name in strategies.items():
        if key in results:
            initial_value = results[key].get('initial_value', 100000)
            final_value = results[key].get('final_value', initial_value)
            metrics_dict[name] = {
                'return': (final_value / initial_value - 1) * 100,
                'sharpe': results[key].get('sharpe_ratio', 0),
                'win_rate': results[key].get('win_rate', 0) * 100 if 'win_rate' in results[key] else 0,
                'max_dd': results[key].get('max_drawdown', 0) * 100 if 'max_drawdown' in results[key] else 0
            }
    
    initial_value = results['buy_and_hold'].get('initial_value', 100000)
    final_value = results['buy_and_hold'].get('final_value', results['buy_and_hold']['portfolio_values'][-1])
    metrics_dict['买入持有'] = {
        'return': (final_value / initial_value - 1) * 100,
        'sharpe': 0,
        'win_rate': 0,
        'max_dd': 0
    }
    
    textstr = '\n'.join([
        f"{name}: R:{info['return']:+.1f}% SR:{info['sharpe']:.2f} WR:{info['win_rate']:.1f}% DD:{info['max_dd']:.1f}%"
        for name, info in metrics_dict.items()
    ])
    
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
           verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # 美化
    plt.tight_layout()
    
    # 保存图片
    output_path = r'E:\pycharm\stock-analysis\records\v75_backtest_with_trades.png'
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    print(f"[OK] 图片已保存: {output_path}")
    
    # 显示
    plt.show()


if __name__ == '__main__':
    main()
