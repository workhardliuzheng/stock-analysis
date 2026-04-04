#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股市分析系统 - 信号分析报告生成模块

功能: 将信号计算结果转化为专业的投资建议报告
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from datetime import datetime
import pandas as pd
import numpy as np


def generate_signal_report(signals, indices_info=None):
    """
    生成信号分析报告
    
    Args:
        signals: 字典，格式为 {'000688.SH': {'total_rows': 282, 'buy_signals': 62, 'sell_signals': 133, 'hold_signals': 87}, ...}
        indices_info: 字典，index code到名称的映射
    
    Returns:
        report: 报告字符串
    """
    if indices_info is None:
        indices_info = {
            '000688.SH': '科创50',
            '399006.SZ': '创业板指',
            '000001.SH': '上证综指',
            '000905.SH': '中证500',
            '000852.SH': '中证1000'
        }
    
    # 构建DataFrame
    data = []
    for code, stats in signals.items():
        total = stats['total_rows']
        buy_pct = stats['buy_signals'] / total * 100 if total > 0 else 0
        sell_pct = stats['sell_signals'] / total * 100 if total > 0 else 0
        hold_pct = stats['hold_signals'] / total * 100 if total > 0 else 0
        
        # 计算信号强度（BUY-SELL差值）
        signal_strength = buy_pct - sell_pct
        
        # 计算信号频率（BUY+SELL占比）
        signal_frequency = buy_pct + sell_pct
        
        data.append({
            '指数': indices_info.get(code, code),
            '代码': code,
            'BUY%': buy_pct,
            'SELL%': sell_pct,
            'HOLD%': hold_pct,
            '信号强度': signal_strength,
            '信号频率': signal_frequency,
            'BUY数': stats['buy_signals'],
            'SELL数': stats['sell_signals'],
            'HOLD数': stats['hold_signals']
        })
    
    df = pd.DataFrame(data)
    
    # 生成报告
    report = []
    report.append("=" * 80)
    report.append("[OK] 股市分析系统 - 信号分析报告")
    report.append(f"[OK] 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    report.append("")
    
    # 1. 摘要
    report.append("[OK] [摘要]")
    total_buy = df['BUY数'].sum()
    total_sell = df['SELL数'].sum()
    total_hold = df['HOLD数'].sum()
    total_all = total_buy + total_sell + total_hold
    
    report.append(f"[OK] 信号统计:")
    report.append(f"   BUY信号: {total_buy:,} ({total_buy/total_all*100:.1f}%)")
    report.append(f"   SELL信号: {total_sell:,} ({total_sell/total_all*100:.1f}%)")
    report.append(f"   HOLD信号: {total_hold:,} ({total_hold/total_all*100:.1f}%)")
    report.append(f"   总信号频率: {(total_buy+total_sell)/total_all*100:.1f}%")
    report.append("")
    
    # 2. 指数详情
    report.append("=" * 80)
    report.append("[OK] [指数信号详情]")
    report.append("=" * 80)
    report.append("")
    
    for _, row in df.iterrows():
        report.append(f"{row['指数']} ({row['代码']})")
        report.append(f"   BUY信号: {int(row['BUY数'])} ({row['BUY%']:.1f}%)")
        report.append(f"   SELL信号: {int(row['SELL数'])} ({row['SELL%']:.1f}%)")
        report.append(f"   HOLD信号: {int(row['HOLD数'])} ({row['HOLD%']:.1f}%)")
        report.append(f"   信号强度: {row['信号强度']:+.1f}")
        report.append(f"   信号频率: {row['信号频率']:.1f}%")
        report.append("")
    
    # 3. 投资建议
    report.append("=" * 80)
    report.append("[投资建议]")
    report.append("=" * 80)
    report.append("")
    
    # 根据信号强度排序
    df_sorted = df.sort_values('信号强度', ascending=False)
    
    # 买入建议
    strong_buy = df_sorted[df_sorted['信号强度'] > 10]
    moderate_buy = df_sorted[(df_sorted['信号强度'] > 0) & (df_sorted['信号强度'] <= 10)]
    neutral = df_sorted[(df_sorted['信号强度'] >= -5) & (df_sorted['信号强度'] <= 5)]
    moderate_sell = df_sorted[(df_sorted['信号强度'] < -5) & (df_sorted['信号强度'] >= -15)]
    strong_sell = df_sorted[df_sorted['信号强度'] < -15]
    
    if len(strong_buy) > 0:
        for _, row in strong_buy.iterrows():
            report.append(f"   - {row['指数']} - {row['BUY%']:.1f}% BUY / {row['SELL%']:.1f}% SELL")
    else:
        report.append("   - 无 -")
    report.append("")
    
    report.append("[OK] **推荐买入** (0 < 信号强度 <= 10):")
    if len(moderate_buy) > 0:
        for _, row in moderate_buy.iterrows():
            report.append(f"   - {row['指数']} - {row['BUY%']:.1f}% BUY / {row['SELL%']:.1f}% SELL")
    else:
        report.append("   - 无 -")
    report.append("")
    
    report.append("[OK] **中性观望** (-5 <= 信号强度 <= 5):")
    if len(neutral) > 0:
        for _, row in neutral.iterrows():
            report.append(f"   - {row['指数']} - {row['BUY%']:.1f}% BUY / {row['SELL%']:.1f}% SELL")
    else:
        report.append("   - 无 -")
    report.append("")
    
    report.append("[OK] **谨慎卖出** (-15 <= 信号强度 < -5):")
    if len(moderate_sell) > 0:
        for _, row in moderate_sell.iterrows():
            report.append(f"   - {row['指数']} - {row['BUY%']:.1f}% BUY / {row['SELL%']:.1f}% SELL")
    else:
        report.append("   - 无 -")
    report.append("")
    
    report.append("[OK] **强烈建议卖出** (信号强度 < -15):")
    if len(strong_sell) > 0:
        for _, row in strong_sell.iterrows():
            report.append(f"   - {row['指数']} - {row['BUY%']:.1f}% BUY / {row['SELL%']:.1f}% SELL")
    else:
        report.append("   - 无 -")
    report.append("")
    
    # 4. 仓位建议
    report.append("=" * 80)
    report.append("[OK] [仓位建议]")
    report.append("=" * 80)
    report.append("")
    
    # 基于信号频率的仓位建议
    high_frequency = df_sorted[df_sorted['信号频率'] > 65]
    medium_frequency = df_sorted[(df_sorted['信号频率'] > 50) & (df_sorted['信号频率'] <= 65)]
    low_frequency = df_sorted[df_sorted['信号频率'] <= 50]
    
    report.append("[OK] **高活跃度策略** (信号频率 > 65%):")
    report.append("   建议仓位: 70-80%")
    report.append("   交易频率: 2-3次/周")
    report.append("   止损策略: -3%以下坚决止损")
    if len(high_frequency) > 0:
        for _, row in high_frequency.iterrows():
            report.append(f"   - {row['指数']} - {row['信号频率']:.1f}% 信号频率")
    else:
        report.append("   - 无 -")
    report.append("")
    
    report.append("[OK] **平衡策略** (50% < 信号频率 <= 65%):")
    report.append("   建议仓位: 50-60%")
    report.append("   交易频率: 1-2次/周")
    report.append("   止损策略: -5%以下考虑止损")
    if len(medium_frequency) > 0:
        for _, row in medium_frequency.iterrows():
            report.append(f"   - {row['指数']} - {row['信号频率']:.1f}% 信号频率")
    else:
        report.append("   - 无 -")
    report.append("")
    
    report.append("[OK] **低活跃度策略** (信号频率 <= 50%):")
    report.append("   建议仓位: 20-30%")
    report.append("   交易频率: 1次/周或更少")
    report.append("   止损策略: -8%以下考虑止损")
    if len(low_frequency) > 0:
        for _, row in low_frequency.iterrows():
            report.append(f"   - {row['指数']} - {row['信号频率']:.1f}% 信号频率")
    else:
        report.append("   - 无 -")
    report.append("")
    
    # 5. 组合建议
    report.append("=" * 80)
    report.append("[OK] [组合建议]")
    report.append("=" * 80)
    report.append("")
    
    # 根据信号强度分配权重
    total_strength = df['信号强度'].abs().sum()
    
    report.append("[OK] **推荐组合** (基于信号强度加权):")
    for _, row in df_sorted.iterrows():
        weight = (row['信号强度'] + 20) / 40 * 100  # 映射到0-100
        weight = max(0, min(100, weight))
        report.append(f"   {row['指数']}: {weight:.1f}% 权重")
    report.append("")
    
    # 总体市场情绪
    avg_strength = df['信号强度'].mean()
    avg_frequency = df['信号频率'].mean()
    
    if avg_strength > 5:
        sentiment = "[OK] 牛市情绪 - 市场普遍看涨"
        risk_level = "偏高"
    elif avg_strength > -5:
        sentiment = "[OK] 震荡行情 - 市场方向不明"
        risk_level = "中等"
    else:
        sentiment = "[OK] 熊市情绪 - 市场普遍看跌"
        risk_level = "偏低"
    
    report.append("=" * 80)
    report.append("[OK] [市场情绪]")
    report.append("=" * 80)
    report.append("")
    report.append(f"[OK] 市场趋势: {sentiment}")
    report.append(f"[OK] 平均信号强度: {avg_strength:.1f}")
    report.append(f"[OK] 平均信号频率: {avg_frequency:.1f}%")
    report.append(f"[OK] 风险等级: {risk_level}")
    report.append("")
    
    report.append("=" * 80)
    report.append("[OK] [免责声明]")
    report.append("=" * 80)
    report.append("本报告仅供参考，不构成投资建议。股市有风险，投资需谨慎。")
    report.append("")
    
    return "\n".join(report)


def get_position_recommendations(signals, indices_info=None):
    """
    获取仓位建议
    
    Args:
        signals: 信号数据
        indices_info: 指数信息
    
    Returns:
        positions: 仓位建议字典
    """
    if indices_info is None:
        indices_info = {
            '000688.SH': '科创50',
            '399006.SZ': '创业板指',
            '000001.SH': '上证综指',
            '000905.SH': '中证500',
            '000852.SH': '中证1000'
        }
    
    positions = {}
    
    for code, stats in signals.items():
        total = stats['total_rows']
        buy_pct = stats['buy_signals'] / total * 100 if total > 0 else 0
        sell_pct = stats['sell_signals'] / total * 100 if total > 0 else 0
        hold_pct = stats['hold_signals'] / total * 100 if total > 0 else 0
        signal_strength = buy_pct - sell_pct
        
        # 基础仓位
        if signal_strength > 15:
            base_position = 0.80
        elif signal_strength > 5:
            base_position = 0.65
        elif signal_strength > -5:
            base_position = 0.50
        elif signal_strength > -15:
            base_position = 0.35
        else:
            base_position = 0.20
        
        # 根据信号频率调整
        signal_frequency = buy_pct + sell_pct
        if signal_frequency > 70:
            adjustment = 0.10
        elif signal_frequency > 60:
            adjustment = 0.05
        elif signal_frequency < 40:
            adjustment = -0.10
        else:
            adjustment = 0.0
        
        final_position = min(0.95, max(0.05, base_position + adjustment))
        
        positions[code] = {
            '指数': indices_info.get(code, code),
            '建议仓位': f"{final_position*100:.0f}%",
            '信号强度': signal_strength,
            '信号频率': signal_frequency,
            'BUY%': buy_pct,
            'SELL%': sell_pct,
            'HOLD%': hold_pct,
            '操作建议': '买入' if signal_strength > 5 else ('卖出' if signal_strength < -5 else '维持')
        }
    
    return positions


def print_position_report(positions):
    """打印仓位报告"""
    report = []
    report.append("=" * 80)
    report.append("📊 仓位建议报告")
    report.append("=" * 80)
    report.append("")
    report.append(f"{'指数':<10} {'建议仓位':<12} {'信号强度':<12} {'信号频率':<12} {'操作建议':<10}")
    report.append("-" * 80)
    
    for code, data in sorted(positions.items(), key=lambda x: x[1]['信号强度'], reverse=True):
        report.append(f"{data['指数']:<10} {data['建议仓位']:<12} {data['信号强度']+20:<12.1f} {data['信号频率']:<12.1f} {data['操作建议']:<10}")
    
    report.append("")
    
    # 总体仓位
    total_position = sum(float(data['建议仓位'].replace('%', '')) for data in positions.values()) / len(positions)
    report.append(f"[OK] 组合建议仓位: {total_position*100:.0f}%")
    report.append("")
    
    return "\n".join(report)


if __name__ == "__main__":
    # 测试数据
    signals = {
        '000688.SH': {'total_rows': 282, 'buy_signals': 62, 'sell_signals': 133, 'hold_signals': 87},
        '399006.SZ': {'total_rows': 297, 'buy_signals': 106, 'sell_signals': 120, 'hold_signals': 71},
        '000001.SH': {'total_rows': 297, 'buy_signals': 38, 'sell_signals': 182, 'hold_signals': 77},
        '000905.SH': {'total_rows': 282, 'buy_signals': 50, 'sell_signals': 166, 'hold_signals': 66},
        '000852.SH': {'total_rows': 282, 'buy_signals': 32, 'sell_signals': 168, 'hold_signals': 82}
    }
    
    print(generate_signal_report(signals))
    print("\n")
    positions = get_position_recommendations(signals)
    print(print_position_report(positions))
