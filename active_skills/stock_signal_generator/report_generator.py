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

# 导入持仓建议模块
from position_advisor import calculate_position_score, get_position_advice, generate_position_report, get_position_dict


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
    获取仓位建议 (使用新的position_advisor模块)
    
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
    
    # 使用position_advisor计算分数
    df_score = calculate_position_score(signals, indices_info)
    
    # 获取仓位建议
    df_advice = get_position_advice(df_score)
    
    # 返回字典格式
    return get_position_dict(df_advice)


def print_position_report(positions):
    """打印仓位报告 (使用新的position_advisor)"""
    # 构建DataFrame，包含所有必要列
    data = []
    for code, info in positions.items():
        data.append({
            '代码': code,
            '指数': info['指数'],
            '建议仓位': f"{int(info['建议仓位']*100)}%",
            '信号强度': info['信号强度'],
            '信号频率': info['信号频率'],
            '操作建议': info['操作建议'],
            '操作描述': info.get('操作描述', ''),
            '风险等级': info.get('风险等级', ''),
            '风险说明': info.get('风险说明', ''),
            'BUY%': info.get('BUY%', 0),
            'SELL%': info.get('SELL%', 0),
            'HOLD%': info.get('HOLD%', 0),
            '总分': info.get('总分', 50),
            '紧急预警': info.get('紧急预警', [])
        })
    
    df = pd.DataFrame(data)
    
    # 生成完整报告
    return generate_position_report(df)


if __name__ == "__main__":
    # 测试数据
    signals = {
        '000688.SH': {'total_rows': 282, 'buy_signals': 62, 'sell_signals': 33, 'hold_signals': 187},
        '399006.SZ': {'total_rows': 297, 'buy_signals': 106, 'sell_signals': 50, 'hold_signals': 141},
        '000001.SH': {'total_rows': 297, 'buy_signals': 38, 'sell_signals': 82, 'hold_signals': 177},
        '000905.SH': {'total_rows': 282, 'buy_signals': 80, 'sell_signals': 30, 'hold_signals': 172},
        '000852.SH': {'total_rows': 282, 'buy_signals': 32, 'sell_signals': 98, 'hold_signals': 152}
    }
    
    # 计算仓位建议
    positions = get_position_recommendations(signals)
    
    # 打印报告
    print(print_position_report(positions))
    
    print(generate_signal_report(signals))
    print("\n")
    positions = get_position_recommendations(signals)
    print(print_position_report(positions))
