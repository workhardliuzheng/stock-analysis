#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股市分析系统 - 投资顾问模块

功能: 基于信号分析提供明确的买卖决策和投资建议
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from datetime import datetime
import pandas as pd
import numpy as np


def generate_investment_advice(signals, indices_info=None, market_context=None):
    """
    生成投资建议报告
    
    Args:
        signals: 信号数据字典
        indices_info: 指数信息映射
        market_context: 市场背景信息
    
    Returns:
        report: 投资建议报告字符串
    """
    if indices_info is None:
        indices_info = {
            '000688.SH': '科创50',
            '399006.SZ': '创业板指',
            '000001.SH': '上证综指',
            '000905.SH': '中证500',
            '000852.SH': '中证1000'
        }
    
    if market_context is None:
        market_context = {
            'market_trend': '震荡偏空',
            'volume': '中等',
            'sentiment': '谨慎'
        }
    
    # 构建DataFrame
    data = []
    for code, stats in signals.items():
        total = stats['total_rows']
        buy_pct = stats['buy_signals'] / total * 100 if total > 0 else 0
        sell_pct = stats['sell_signals'] / total * 100 if total > 0 else 0
        hold_pct = stats['hold_signals'] / total * 100 if total > 0 else 0
        signal_strength = buy_pct - sell_pct
        signal_frequency = buy_pct + sell_pct
        
        data.append({
            '代码': code,
            '指数': indices_info.get(code, code),
            'BUY%': round(buy_pct, 1),
            'SELL%': round(sell_pct, 1),
            'HOLD%': round(hold_pct, 1),
            '信号强度': round(signal_strength, 1),
            '信号频率': round(signal_frequency, 1),
            'BUY数': stats['buy_signals'],
            'SELL数': stats['sell_signals']
        })
    
    df = pd.DataFrame(data)
    
    # 按信号强度排序
    df_sorted = df.sort_values('信号强度', ascending=False)
    
    # 生成报告
    report = []
    report.append("=" * 80)
    report.append("[OK] 股市分析系统 - 投资顾问报告")
    report.append(f"[OK] 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    report.append("")
    
    # 1. 市场概览
    report.append("[OK]【市场概览】")
    report.append(f"-{market_context['market_trend']}")
    report.append(f"-交易量: {market_context['volume']}")
    report.append(f"-市场情绪: {market_context['sentiment']}")
    report.append("")
    
    # 2. 核心结论
    avg_strength = df['信号强度'].mean()
    avg_frequency = df['信号频率'].mean()
    total_buy = df['BUY数'].sum()
    total_sell = df['SELL数'].sum()
    
    report.append("[OK]【核心结论】")
    if avg_strength > 10:
        report.append(f"[OK] 强烈看涨: 平均信号强度 +{avg_strength:.1f}")
        report.append(f"   建议仓位: 80-90%")
        report.append(f"   策略: 加仓/逢低吸纳")
    elif avg_strength > 5:
        report.append(f"[OK] 看涨: 平均信号强度 +{avg_strength:.1f}")
        report.append(f"   建议仓位: 60-70%")
        report.append(f"   策略: 维持/逢低吸纳")
    elif avg_strength > -5:
        report.append(f"[OK] 震荡: 平均信号强度 {avg_strength:.1f}")
        report.append(f"   建议仓位: 40-50%")
        report.append(f"   策略: 持仓观察/波段操作")
    elif avg_strength > -15:
        report.append(f"[OK] 看跌: 平均信号强度 {avg_strength:.1f}")
        report.append(f"   建议仓位: 20-30%")
        report.append(f"   策略: 减仓/控制风险")
    else:
        report.append(f"[OK] 强烈看跌: 平均信号强度 {avg_strength:.1f}")
        report.append(f"   建议仓位: 10-20%")
        report.append(f"   策略: 大幅减仓/空仓观望")
    
    report.append(f"-总信号: BUY={total_buy}, SELL={total_sell}")
    report.append(f"-信号频率: {avg_frequency:.1f}%")
    report.append("")
    
    # 3. 指数分析
    report.append("=" * 80)
    report.append("[OK]【个股/指数详细分析】")
    report.append("=" * 80)
    report.append("")
    
    # 按信号强度排序
    df_sorted = df.sort_values('信号强度', ascending=False)
    
    for i, (_, row) in enumerate(df_sorted.iterrows(), 1):
        code = row['代码']
        index_name = row['指数']
        buy_pct = row['BUY%']
        sell_pct = row['SELL%']
        signal_strength = row['信号强度']
        signal_frequency = row['信号频率']
        buy_num = int(row['BUY数'])
        sell_num = int(row['SELL数'])
        
        # 判断买卖结论
        if signal_strength > 10:
            advice = "BUY | 买入"
            action = "买入/加仓"
            position = "60-80%"
            confidence = "高"
        elif signal_strength > 5:
            advice = "BUY | 买入"
            action = "逢低吸纳"
            position = "50-60%"
            confidence = "中高"
        elif signal_strength > -5:
            advice = "HOLD | 持仓"
            action = "观望/波段"
            position = "30-40%"
            confidence = "低"
        elif signal_strength > -15:
            advice = "SELL | 卖出"
            action = "逢高减仓"
            position = "10-20%"
            confidence = "中高"
        else:
            advice = "SELL | 卖出"
            action = "大幅减仓/空仓"
            position = "0-10%"
            confidence = "高"
        
        report.append(f"[OK] {i}. {index_name} ({code})")
        report.append(f"-当前信号: {advice}")
        report.append(f"-信号强度: {signal_strength:+.1f} (BUY {buy_pct:.1f}% / SELL {sell_pct:.1f}%)")
        report.append(f"-信号频率: {signal_frequency:.1f}%")
        report.append(f"-操作建议: {action}")
        report.append(f"-建议仓位: {position}")
        report.append(f"-信号统计: BUY={buy_num}条, SELL={sell_num}条")
        report.append(f"-信心度: {confidence}")
        
        # 添加分析理由
        if signal_strength > 0:
            report.append(f"-分析: SELL信号偏多，当前处于卖出区域")
        else:
            report.append(f"-分析: BUY信号偏多，当前处于买入区域")
        
        if signal_frequency > 70:
            report.append(f"-风险: 信号频繁，建议快进快出")
        elif signal_frequency < 40:
            report.append(f"-风险: 信号稀少，建议谨慎观望")
        
        report.append("")
    
    # 4. 组合建议
    report.append("=" * 80)
    report.append("[OK]【投资组合建议】")
    report.append("=" * 80)
    report.append("")
    
    # 计算推荐组合
    strong_buy = df_sorted[df_sorted['信号强度'] > 5]
    moderate_buy = df_sorted[(df_sorted['信号强度'] > -5) & (df_sorted['信号强度'] <= 5)]
    sell_candidates = df_sorted[df_sorted['信号强度'] <= -5]
    
    report.append("[OK] 推荐买入组合 (信号强度 > 5):")
    if len(strong_buy) > 0:
        for _, row in strong_buy.iterrows():
            report.append(f"-{row['指数']}: {row['BUY%']:.1f}% BUY, {row['SELL%']:.1f}% SELL")
    else:
        report.append("-无")
    
    report.append("")
    report.append("[OK] 谨慎持有组合 (信号强度 -5 ~ 5):")
    if len(moderate_buy) > 0:
        for _, row in moderate_buy.iterrows():
            report.append(f"-{row['指数']}: {row['BUY%']:.1f}% BUY, {row['SELL%']:.1f}% SELL")
    else:
        report.append("-无")
    
    report.append("")
    report.append("[OK] 建议卖出组合 (信号强度 <= -5):")
    if len(sell_candidates) > 0:
        for _, row in sell_candidates.iterrows():
            report.append(f"-{row['指数']}: {row['BUY%']:.1f}% BUY, {row['SELL%']:.1f}% SELL")
            # 具体卖出建议
            if row['SELL%'] > 50:
                report.append(f"  -> 明确建议: 减仓/逢高卖出")
            elif row['SELL%'] > 40:
                report.append(f"  -> 建议: 控制仓位/逢高部分减仓")
    else:
        report.append("-无")
    
    report.append("")
    
    # 5. 具体操作建议
    report.append("=" * 80)
    report.append("[OK]【具体操作建议】")
    report.append("=" * 80)
    report.append("")
    
    # 买入建议
    report.append("[OK] 买入机会:")
    buy_opportunities = df_sorted[df_sorted['SELL%'] > 50]
    if len(buy_opportunities) > 0:
        for _, row in buy_opportunities.iterrows():
            report.append(f"-{row['指数']}: SELL信号高达 {row['SELL%']:.1f}%，建议分批建仓")
    else:
        report.append("-当前市场没有明显的买入机会")
    
    report.append("")
    
    # 卖出建议
    report.append("[OK] 卖出机会:")
    sell_opportunities = df_sorted[df_sorted['SELL%'] > 40]
    if len(sell_opportunities) > 0:
        for _, row in sell_opportunities.iterrows():
            if row['SELL%'] > 50:
                report.append(f"-{row['指数']}: SELL信号 {row['SELL%']:.1f}%，**强烈建议** 减仓")
            else:
                report.append(f"-{row['指数']}: SELL信号 {row['SELL%']:.1f}%，建议适度减仓")
    else:
        report.append("-当前市场没有明显的卖出机会")
    
    report.append("")
    
    # 紧急建议
    report.append("[OK] 紧急操作建议:")
    urgent_sells = df_sorted[df_sorted['SELL%'] > 60]
    if len(urgent_sells) > 0:
        for _, row in urgent_sells.iterrows():
            report.append(f"[WARNING] {row['指数']}: SELL信号高达 {row['SELL%']:.1f}%，**立即减仓**")
    else:
        report.append("-无紧急操作需求")
    
    report.append("")
    
    # 6. 仓位管理
    report.append("=" * 80)
    report.append("[OK]【仓位管理建议】")
    report.append("=" * 80)
    report.append("")
    
    # 总体仓位
    recommended_position = max(10, min(90, 40 + avg_strength * 2))
    report.append(f"[OK] 总体仓位建议: {recommended_position:.0f}%")
    
    report.append("")
    report.append("[OK] 具体分配:")
    
    # 分配建议
    for _, row in df_sorted.iterrows():
        code = row['代码']
        index_name = row['指数']
        signal_strength = row['信号强度']
        
        if signal_strength > 10:
            weight = 20
        elif signal_strength > 5:
            weight = 15
        elif signal_strength > -5:
            weight = 10
        elif signal_strength > -15:
            weight = 5
        else:
            weight = 0
        
        report.append(f"-{index_name}: {weight:.0f}%")
    
    total_weight = sum(min(20, max(0, 10 + row['信号强度'] * 1)) for _, row in df_sorted.iterrows())
    if total_weight > 0:
        report.append(f"-合计: {total_weight:.0f}%")
    
    report.append("")
    
    # 7. 风险提示
    report.append("=" * 80)
    report.append("[OK]【风险提示】")
    report.append("=" * 80)
    report.append("")
    
    if avg_strength < -10:
        report.append("[WARNING] 市场风险: 高 - 建议大幅减仓")
    elif avg_strength < -5:
        report.append("[WARNING] 市场风险: 中高 - 建议减仓")
    elif avg_strength > 5:
        report.append("[OK] 市场风险: 低 - 适量加仓")
    else:
        report.append("[OK] 市场风险: 中等 - 控制仓位")
    
    report.append("")
    report.append("[OK] 建议:")
    report.append("-1. 设置止损: 单笔亏损不超过本金的3%")
    report.append("-2. 分批建仓: 避免一次性买入")
    report.append("-3. 控制仓位: 根据信号动态调整")
    report.append("-4. 严格执行: 不情绪化交易")
    
    report.append("")
    report.append("=" * 80)
    report.append("[OK]【免责声明】")
    report.append("=" * 80)
    report.append("本报告仅供参考，不构成投资建议。股市有风险，投资需谨慎。")
    
    return "\n".join(report)


def get_clear_trading_signals(signals, indices_info=None):
    """
    获取明确的交易信号列表
    
    Args:
        signals: 信号数据
        indices_info: 指数信息
    
    Returns:
        signals_list: 交易信号列表
    """
    if indices_info is None:
        indices_info = {
            '000688.SH': '科创50',
            '399006.SZ': '创业板指',
            '000001.SH': '上证综指',
            '000905.SH': '中证500',
            '000852.SH': '中证1000'
        }
    
    signals_list = []
    
    for code, stats in signals.items():
        total = stats['total_rows']
        buy_pct = stats['buy_signals'] / total * 100 if total > 0 else 0
        sell_pct = stats['sell_signals'] / total * 100 if total > 0 else 0
        signal_strength = buy_pct - sell_pct
        
        # 确定建议
        if signal_strength > 5:
            action = "BUY"
            confidence = "高"
        elif signal_strength > -5:
            action = "HOLD"
            confidence = "中"
        else:
            action = "SELL"
            confidence = "高"
        
        signals_list.append({
            '指数': indices_info.get(code, code),
            '代码': code,
            '信号强度': round(signal_strength, 1),
            '建议操作': action,
            '建议仓位': f"{min(90, max(10, 40 + signal_strength * 2)):.0f}%",
            'confidence': confidence
        })
    
    # 按信号强度排序
    signals_list.sort(key=lambda x: x['信号强度'], reverse=True)
    
    return signals_list


def print_trading_signals(signals_list):
    """打印交易信号列表"""
    report = []
    report.append("=" * 80)
    report.append("_[OK] 交易信号速览")
    report.append("=" * 80)
    report.append("")
    report.append(f"{'指数':<10} {'信号强度':<12} {'建议操作':<10} {'建议仓位':<12} {'置信度':<8}")
    report.append("-" * 80)
    
    for item in signals_list:
        report.append(f"{item['指数']:<10} {item['信号强度']:+.1f}     {item['建议操作']:<10} {item['建议仓位']:<12} {item['confidence']:<8}")
    
    report.append("")
    report.append("=" * 80)
    report.append("[OK] 技术说明:")
    report.append("-信号强度 = BUY% - SELL%")
    report.append("-信号强度 > 5: 强烈买入信号")
    report.append("-信号强度 -5 ~ 5: 持仓观望")
    report.append("-信号强度 < -5: 卖出信号")
    report.append("=" * 80)
    
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
    
    # 生成投资建议报告
    print(generate_investment_advice(signals))
    print("\n")
    
    # 打印交易信号
    signals_list = get_clear_trading_signals(signals)
    print(print_trading_signals(signals_list))
