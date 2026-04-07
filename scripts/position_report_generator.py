#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""持仓建议报告生成（使用position_advisor）"""

import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from datetime import datetime
from active_skills.stock_signal_generator.position_advisor import (
    calculate_position_score, get_position_advice, generate_position_report, get_position_dict
)

def generate_report():
    # 测试数据（模拟信号）
    signals = {
        '000688.SH': {'total_rows': 282, 'buy_signals': 62, 'sell_signals': 33, 'hold_signals': 187},
        '399006.SZ': {'total_rows': 297, 'buy_signals': 106, 'sell_signals': 50, 'hold_signals': 141},
        '000001.SH': {'total_rows': 297, 'buy_signals': 38, 'sell_signals': 82, 'hold_signals': 177},
        '000905.SH': {'total_rows': 282, 'buy_signals': 80, 'sell_signals': 30, 'hold_signals': 172},
        '000852.SH': {'total_rows': 282, 'buy_signals': 32, 'sell_signals': 98, 'hold_signals': 152}
    }
    
    # 计算分数
    df_score = calculate_position_score(signals)
    
    # 获取仓位建议
    df_advice = get_position_advice(df_score)
    
    # 生成报告
    report = generate_position_report(df_advice)
    
    # 保存到文件
    output_file = r'E:\pycharm\stock-analysis\records\持仓建议报告_20260407_V2.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"[OK] 报告已保存到: {output_file}")
    return report

if __name__ == "__main__":
    report = generate_report()
    # 同时打印到控制台（UTF-8编码）
    print("\n" + "="*80)
    print("报告内容：")
    print("="*80)
    print(report)
