#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
持仓比例建议模块

功能: 根据信号分析结果，给出明确的持仓比例建议
"""

import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from datetime import datetime
import pandas as pd


def calculate_position_score(signals, indices_info=None):
    """
    计算每个指数的持仓分数
    
    分数范围: 0-100，越高表示越应该重仓
    
    计算逻辑:
    1. 信号强度 (0-40分): BUY% - SELL%，范围-100~100，映射到0-40
    2. 信号频率 (0-30分): BUY% + SELL%，越高表示机会越多
    3. 市场状态 (0-30分): 根据综合信号判断牛/熊/震荡
    """
    if indices_info is None:
        indices_info = {
            '000688.SH': '科创50',
            '399006.SZ': '创业板指',
            '000001.SH': '上证综指',
            '000905.SH': '中证500',
            '000852.SH': '中证1000',
            '399001.SZ': '深证成指',
            '000300.SH': '沪深300'
        }
    
    data = []
    
    for code, stats in signals.items():
        total = stats['total_rows']
        buy_pct = stats['buy_signals'] / total * 100 if total > 0 else 0
        sell_pct = stats['sell_signals'] / total * 100 if total > 0 else 0
        hold_pct = stats['hold_signals'] / total * 100 if total > 0 else 0
        
        # 信号强度 (-100到+100)
        signal_strength = buy_pct - sell_pct
        
        # 信号频率 (0到100)
        signal_frequency = buy_pct + sell_pct
        
        # 基础分数计算
        # 1. 信号强度分 (0-40): 映射 -100~100 → 0~40
        strength_score = max(0, min(40, (signal_strength + 100) / 5))
        
        # 2. 信号频率分 (0-30): 映射 0~100 → 0~30
        frequency_score = signal_frequency * 0.3
        
        # 3. 市场状态分 (0-30)
        # 综合判断市场状态
        if signal_strength > 10:
            market_score = 30  # 牛市
        elif signal_strength > -5:
            market_score = 20  # 震荡
        else:
            market_score = 10  # 熊市
        
        # 总分
        total_score = strength_score + frequency_score + market_score
        
        data.append({
            '代码': code,
            '指数': indices_info.get(code, code),
            'BUY%': buy_pct,
            'SELL%': sell_pct,
            'HOLD%': hold_pct,
            '信号强度': signal_strength,
            '信号频率': signal_frequency,
            '信号强度分': strength_score,
            '信号频率分': frequency_score,
            '市场状态分': market_score,
            '总分': total_score,
            '总rows': total,
            'BUY数': stats['buy_signals'],
            'SELL数': stats['sell_signals'],
            'HOLD数': stats['hold_signals']
        })
    
    return pd.DataFrame(data)


def get_position_advice(df):
    """
    根据分数给出持仓建议
    
    返回每个指数的:
    - 仓位建议 (0-100%)
    - 操作建议 (HOLD/BUY/SELL)
    - 风险等级 (低/中/高)
    - 紧急预警 (如有)
    """
    
    # 基础仓位基于总分 (0-100分 → 0-95%仓位)
    def calc_base_position(score):
        # 50分 = 50%仓位
        # 80分 = 80%仓位
        # 20分 = 20%仓位
        return min(95, max(5, score * 0.95))
    
    # 根据信号强度判断操作
    def get_operation(strength):
        if strength > 10:
            return 'BUY', '强烈看涨'
        elif strength > 5:
            return 'BUY', '看涨'
        elif strength > -5:
            return 'HOLD', '中性'
        elif strength > -10:
            return 'SELL', '看跌'
        else:
            return 'SELL', '强烈看跌'
    
    # 根据信号频率判断风险
    def get_risk(frequency):
        if frequency > 70:
            return '高', '信号频繁，机会多但需注意假信号'
        elif frequency > 50:
            return '中', '信号适中，可正常交易'
        else:
            return '低', '信号稀少，建议减少操作'
    
    # 检查紧急预警
    def check_alert(row):
        alerts = []
        
        # SELL信号过强 (卖出机会)
        if row['SELL%'] > 60:
            alerts.append('[WARNING] SELL信号过强！建议减仓')
        
        # BUY信号过强 (买入机会)
        if row['BUY%'] > 60:
            alerts.append('[OK] BUY信号过强！建议加仓')
        
        # 信号频率过低
        if row['信号频率'] < 30:
            alerts.append('[OK] 信号稀少，建议观望')
        
        return alerts
    
    results = []
    
    for _, row in df.iterrows():
        base_position = calc_base_position(row['总分'])
        
        # 根据信号频率微调
        if row['信号频率'] > 70:
            adjustment = 0.05
        elif row['信号频率'] > 60:
            adjustment = 0.03
        elif row['信号频率'] < 40:
            adjustment = -0.05
        else:
            adjustment = 0.0
        
        final_position = min(95, max(5, base_position + adjustment * 100))
        
        operation, description = get_operation(row['信号强度'])
        risk, risk_desc = get_risk(row['信号频率'])
        
        # 紧急预警
        alerts = check_alert(row)
        
        results.append({
            '代码': row['代码'],
            '指数': row['指数'],
            '建议仓位': f"{final_position:.0f}%",
            '信号强度': row['信号强度'],
            '信号频率': row['信号频率'],
            '操作建议': operation,
            '操作描述': description,
            '风险等级': risk,
            '风险说明': risk_desc,
            'BUY%': row['BUY%'],
            'SELL%': row['SELL%'],
            'HOLD%': row['HOLD%'],
            '总分': row['总分'],
            '紧急预警': alerts
        })
    
    return pd.DataFrame(results)


def generate_position_report(df):
    """生成持仓建议报告"""
    report = []
    
    report.append("=" * 80)
    report.append("[OK] 股市分析系统 - 持仓比例建议")
    report.append(f"[OK] 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    report.append("")
    
    # 摘要
    report.append("[OK] [摘要]")
    avg_position = df['建议仓位'].apply(lambda x: float(x.replace('%', ''))).mean()
    total_buy = df[df['操作建议'] == 'BUY'].shape[0]
    total_sell = df[df['操作建议'] == 'SELL'].shape[0]
    total_hold = df[df['操作建议'] == 'HOLD'].shape[0]
    
    report.append(f"[OK] 组合建议仓位: {avg_position:.0f}%")
    report.append(f"[OK] 买入指数: {total_buy} 个")
    report.append(f"[OK] 卖出指数: {total_sell} 个")
    report.append(f"[OK] 持有指数: {total_hold} 个")
    report.append("")
    
    # 详细建议
    report.append("=" * 80)
    report.append("[OK] [详细持仓建议]")
    report.append("=" * 80)
    report.append("")
    
    for _, row in df.iterrows():
        report.append(f"[OK] {row['指数']} ({row['代码']})")
        report.append(f"   建议仓位: {row['建议仓位']} (当前: {row['总分']:.0f}分)")
        report.append(f"   操作建议: {row['操作建议']} - {row['操作描述']}")
        report.append(f"   风险等级: {row['风险等级']} - {row['风险说明']}")
        report.append(f"   信号分布: BUY {row['BUY%']:.1f}% / SELL {row['SELL%']:.1f}% / HOLD {row['HOLD%']:.1f}%")
        report.append(f"   信号强度: {row['信号强度']:+.1f} / 信号频率: {row['信号频率']:.1f}%")
        
        # 紧急预警
        if row['紧急预警']:
            report.append("   [ALERT] 紧急预警:")
            for alert in row['紧急预警']:
                report.append(f"      {alert}")
        
        report.append("")
    
    # 组合建议
    report.append("=" * 80)
    report.append("[OK] [组合配置建议]")
    report.append("=" * 80)
    report.append("")
    
    # 分类
    high_pos = df[df['建议仓位'].apply(lambda x: float(x.replace('%', ''))) >= 70]
    mid_pos = df[(df['建议仓位'].apply(lambda x: float(x.replace('%', ''))) >= 50) & 
                 (df['建议仓位'].apply(lambda x: float(x.replace('%', ''))) < 70)]
    low_pos = df[df['建议仓位'].apply(lambda x: float(x.replace('%', ''))) < 50]
    
    report.append("[OK] **重仓策略 (70-95%仓位):**")
    if len(high_pos) > 0:
        for _, row in high_pos.iterrows():
            report.append(f"   {row['指数']}: {row['建议仓位']} - {row['操作建议']} ({row['操作描述']})")
    else:
        report.append("   (无此类指数)")
    report.append("")
    
    report.append("[OK] **中仓策略 (50-70%仓位):**")
    if len(mid_pos) > 0:
        for _, row in mid_pos.iterrows():
            report.append(f"   {row['指数']}: {row['建议仓位']} - {row['操作建议']} ({row['操作描述']})")
    else:
        report.append("   (无此类指数)")
    report.append("")
    
    report.append("[OK] **轻仓策略 (<50%仓位):**")
    if len(low_pos) > 0:
        for _, row in low_pos.iterrows():
            report.append(f"   {row['指数']}: {row['建议仓位']} - {row['操作建议']} ({row['操作描述']})")
    else:
        report.append("   (无此类指数)")
    report.append("")
    
    # 总体仓位建议
    report.append("=" * 80)
    report.append("[OK] [总体仓位建议]")
    report.append("=" * 80)
    report.append("")
    
    # 计算最优组合仓位
    # 买入指数按建议仓位，卖出指数减半，持有指数保持50%
    buy_indices = df[df['操作建议'] == 'BUY']
    sell_indices = df[df['操作建议'] == 'SELL']
    hold_indices = df[df['操作建议'] == 'HOLD']
    
    if len(buy_indices) > 0:
        buy_avg = buy_indices['建议仓位'].apply(lambda x: float(x.replace('%', ''))).mean()
    else:
        buy_avg = 80
    
    if len(sell_indices) > 0:
        sell_avg = sell_indices['建议仓位'].apply(lambda x: float(x.replace('%', ''))).mean()
    else:
        sell_avg = 20
    
    hold_avg = 50
    
    # 组合权重基于指数数量
    total_indices = len(df)
    buy_weight = len(buy_indices) / total_indices if total_indices > 0 else 0
    sell_weight = len(sell_indices) / total_indices if total_indices > 0 else 0
    hold_weight = len(hold_indices) / total_indices if total_indices > 0 else 0
    
    portfolio_position = buy_avg * buy_weight + sell_avg * sell_weight + hold_avg * hold_weight
    
    report.append(f"[OK] 建议总仓位: {portfolio_position:.0f}%")
    report.append("")
    report.append("   配置方式:")
    report.append(f"   - 买入指数 ({len(buy_indices)}个): {buy_avg:.0f}% 仓位")
    report.append(f"   - 卖出指数 ({len(sell_indices)}个): {sell_avg:.0f}% 仓位")
    report.append(f"   - 持有指数 ({len(hold_indices)}个): {hold_avg:.0f}% 仓位")
    report.append("")
    
    # 风险提示
    report.append("=" * 80)
    report.append("[OK] [风险提示]")
    report.append("=" * 80)
    report.append("")
    
    if portfolio_position > 85:
        report.append("[WARNING] 建议总仓位过高 (>85%)！请注意控制风险，适当减仓。")
    elif portfolio_position > 75:
        report.append("[OK] 建议总仓位适中 (75-85%)，可正常持仓操作。")
    elif portfolio_position > 55:
        report.append("[OK] 建议总仓位中等 (55-75%)，市场方向不明时的合理仓位。")
    else:
        report.append("[WARNING] 建议总仓位较低 (<55%)，建议等待更多买入信号。")
    
    report.append("")
    report.append("=" * 80)
    report.append("[OK] [免责声明]")
    report.append("=" * 80)
    report.append("本报告仅供参考，不构成投资建议。股市有风险，投资需谨慎。")
    report.append("")
    
    return "\n".join(report)


def get_position_dict(df):
    """返回字典格式的仓位建议"""
    positions = {}
    
    for _, row in df.iterrows():
        positions[row['代码']] = {
            '指数': row['指数'],
            '建议仓位': float(row['建议仓位'].replace('%', '')) / 100,
            '操作建议': row['操作建议'],
            '信号强度': row['信号强度'],
            '信号频率': row['信号频率'],
            'BUY%': row['BUY%'],
            'SELL%': row['SELL%'],
            'HOLD%': row['HOLD%'],
            '风险等级': row['风险等级'],
            '紧急预警': row['紧急预警']
        }
    
    return positions


if __name__ == "__main__":
    # 测试数据
    signals = {
        '000688.SH': {'total_rows': 282, 'buy_signals': 62, 'sell_signals': 33, 'hold_signals': 187},
        '399006.SZ': {'total_rows': 297, 'buy_signals': 106, 'sell_signals': 50, 'hold_signals': 141},
        '000001.SH': {'total_rows': 297, 'buy_signals': 38, 'sell_signals': 82, 'hold_signals': 177},
        '000905.SH': {'total_rows': 282, 'buy_signals': 80, 'sell_signals': 30, 'hold_signals': 172},
        '000852.SH': {'total_rows': 282, 'buy_signals': 32, 'sell_signals': 98, 'hold_signals': 152}
    }
    
    # 计算分数
    df_score = calculate_position_score(signals)
    print(df_score[['指数', '总分', '信号强度', '信号频率', '信号强度分', '信号频率分', '市场状态分']])
    print("\n")
    
    # 获取建议
    df_advice = get_position_advice(df_score)
    print(generate_position_report(df_advice))
    
    # 返回字典
    positions = get_position_dict(df_advice)
    print("\n")
    print("字典格式:")
    for code, data in positions.items():
        print(f"  {code}: {data['建议仓位']*100:.0f}% - {data['操作建议']}")
