#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
回测可视化 - 5年回测结果对比图

功能:
1. 对科创50、中证500、沪深300、上证综指进行5年回测
2. 生成一张图展示：
   - 指数原始走势
   - 买入持有基准
   - 多因子策略
   - ML策略
   - 混合策略（V7-5）

执行:
    python scripts/backtest_visualizer.py --code 000688.SH,000905.SH,000300.SH,000001.SH
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, r'E:\pycharm\stock-analysis')

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime, timedelta

from analysis.index_analyzer import IndexAnalyzer
from analysis.backtester import Backtester
from entity import constant


def get_index_data(ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """获取指数数据并进行分析"""
    print(f"正在获取 {ts_code} 数据...")
    
    analyzer = IndexAnalyzer(ts_code)
    analyzer.analyze(include_ml=True, auto_tune=False)
    
    return analyzer.data


def run_backtest_for_index(ts_code: str, data: pd.DataFrame) -> dict:
    """对单个指数运行回测"""
    print(f"正在回测 {ts_code}...")
    
    bt = Backtester(
        initial_capital=100000,
        commission_rate=0.00006,
        execution_timing='close'
    )
    
    results = {}
    
    # 多因子策略
    if 'factor_signal' in data.columns:
        results['multi_factor'] = bt.run(data, 'factor_signal')
    
    # ML策略
    if 'ml_signal' in data.columns:
        results['ml'] = bt.run(data, 'ml_signal')
    
    # 混合策略 (V7-5)
    if 'final_signal' in data.columns:
        results['combined'] = bt.run(data, 'final_signal')
    
    # 买入持有基准
    # 使用 pct_chg 计算累计收益作为基准
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
        'trades': [],
        'sharpe_ratio': 0.0,
        'win_rate': 0.0
    }
    
    return results


def plot_backtest_comparison(
    all_results: dict,
    start_date: str,
    end_date: str
):
    """绘制回测对比图"""
    n_indices = len(all_results)
    
    fig, axes = plt.subplots(n_indices, 1, figsize=(16, 4 * n_indices))
    if n_indices == 1:
        axes = [axes]
    
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
    plt.rcParams['axes.unicode_minus'] = False
    
    for idx, (index_name, results) in enumerate(all_results.items()):
        ax = axes[idx]
        
        # 基础数据
        dates = pd.to_datetime(results['buy_and_hold']['trade_dates'])
        
        # 绘制指数走势
        ax.plot(dates, results['buy_and_hold']['portfolio_values'], 
                label='买入持有基准', linestyle='--', linewidth=1, alpha=0.7)
        
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
                       linewidth=2, alpha=0.9, color=colors[key])
        
        # 添加买卖点标记
        buy_dates = []
        sell_dates = []
        buy_values = []
        sell_values = []
        
        if 'combined' in results and 'trades' in results['combined']:
            for trade in results['combined']['trades']:
                date = pd.to_datetime(trade['exit_date'] if 'exit_date' in trade else trade.get('entry_date', ''))
                if 'open' not in trade:  # 排除未平仓交易
                    if trade.get('type', '') == 'BUY' and 'entry_date' in trade:
                        if len(dates) > 0 and date >= dates.iloc[0] and date <= dates.iloc[-1]:
                            buy_dates.append(date)
                            pos_idx = max(0, min(len(dates)-1, sum(dates <= date) - 1))
                            buy_values.append(results['combined']['portfolio_values'][pos_idx])
                    elif trade.get('type', '') == 'SELL' and 'exit_date' in trade:
                        if len(dates) > 0 and date >= dates.iloc[0] and date <= dates.iloc[-1]:
                            sell_dates.append(date)
                            pos_idx = max(0, min(len(dates)-1, sum(dates <= date) - 1))
                            sell_values.append(results['combined']['portfolio_values'][pos_idx])
        
        if buy_dates:
            ax.scatter(buy_dates, buy_values, c='red', s=100, marker='^', 
                      label='买入信号', zorder=5)
        if sell_dates:
            ax.scatter(sell_dates, sell_values, c='green', s=100, marker='v', 
                      label='卖出信号', zorder=5)
        
        # 格式化
        ax.set_title(f'{index_name} 回测结果 ({start_date} ~ {end_date})', fontsize=14, fontweight='bold')
        ax.set_ylabel('组合价值 (元)', fontsize=12)
        ax.legend(loc='best', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='x', rotation=45)
        
        # 格式化x轴日期
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        
        # 添加绩效指标文本
        metrics_dict = {}
        for key, name in strategies.items():
            if key in results:
                initial_value = results[key].get('initial_value', 100000)
                final_value = results[key].get('final_value', initial_value)
                metrics_dict[name] = {
                    'return': (final_value / initial_value - 1) * 100,
                    'sharpe': results[key].get('sharpe_ratio', 0),
                    'win_rate': results[key].get('win_rate', 0) * 100 if 'win_rate' in results[key] else 0
                }
        
        # 添加基准指标
        metrics_dict['买入持有'] = {
            'return': (results['buy_and_hold']['final_value'] / results['buy_and_hold']['initial_value'] - 1) * 100,
            'sharpe': results['buy_and_hold']['sharpe_ratio'],
            'win_rate': 0
        }
        
        textstr = '\n'.join([
            f"{name}: {info['return']:+.1f}% (夏普:{info['sharpe']:.2f}, 胜率:{info['win_rate']:.1f}%)"
            for name, info in metrics_dict.items()
        ])
        
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=8,
               verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # 总标题
    fig.suptitle('近5年A股指数回测对比 - 多策略绩效评估', 
                fontsize=16, fontweight='bold', y=0.995)
    
    plt.tight_layout()
    
    # 保存图片
    output_path = r'E:\pycharm\stock-analysis\records\backtest_comparison_5years.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"[OK] 图片已保存: {output_path}")
    
    # 显示
    plt.show()


def main():
    """主函数"""
    print("=" * 60)
    print("[OK] 开始5年回测可视化")
    print("=" * 60)
    
    # 指数列表
    indices = [
        ('科创50', '000688.SH'),
        ('中证500', '000905.SH'),
        ('沪深300', '000300.SH'),
        ('上证综指', '000001.SH'),
    ]
    
    # 时间范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365)  # 5年
    
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')
    
    print(f"[OK] 时间范围: {start_date_str} ~ {end_date_str}")
    print()
    
    all_results = {}
    
    for index_name, ts_code in indices:
        try:
            print(f"[OK] 处理 {index_name} ({ts_code})...")
            
            # 获取数据
            data = get_index_data(ts_code, start_date_str, end_date_str)
            
            # 过滤时间范围
            if 'trade_date' in data.columns:
                # 确保trade_date是数字类型
                data['trade_date_int'] = pd.to_numeric(data['trade_date'], errors='coerce')
                start_date_int = int(start_date_str.replace('-', ''))
                data = data[data['trade_date_int'] >= start_date_int]
                data = data.drop(columns=['trade_date_int'])
            
            if len(data) < 100:
                print(f"[ERROR] {index_name} 数据不足: {len(data)}条")
                continue
            
            # 运行回测
            results = run_backtest_for_index(ts_code, data)
            
            all_results[index_name] = results
            
            print(f"[OK] {index_name} 回测完成")
            print()
            
        except Exception as e:
            print(f"[ERROR] {index_name} 处理失败: {e}")
            import traceback
            traceback.print_exc()
    
    if not all_results:
        print("[ERROR] 没有成功回测的指数")
        return
    
    print("=" * 60)
    print("[OK] 开始生成对比图...")
    print("=" * 60)
    
    # 绘制图表
    plot_backtest_comparison(all_results, start_date_str, end_date_str)
    
    print("=" * 60)
    print("[OK] 回测可视化完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
