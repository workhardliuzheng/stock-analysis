#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查信号列数据"""

import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from mysql_connect.db import get_engine
from sqlalchemy import text

def check_signals():
    engine = get_engine()
    conn = engine.connect()
    
    # 检查final_signal列
    query = """
    SELECT 
        ts_code,
        COUNT(*) as total,
        COUNT(final_signal) as has_signal,
        COUNT_IF(final_signal = 'BUY') as buy_count,
        COUNT_IF(final_signal = 'SELL') as sell_count,
        COUNT_IF(final_signal = 'HOLD') as hold_count
    FROM ts_stock_data
    WHERE ts_code IN ('399001.SZ', '399006.SZ', '000001.SH', '000300.SH', '000688.SH', '000852.SH', '000905.SH', '000016.SH')
    GROUP BY ts_code
    """
    
    result = conn.execute(text(query))
    print("信号列检查结果:")
    for r in result:
        print(f"{r[0]}: total={r[1]}, has_signal={r[2]}, BUY={r[3]}, SELL={r[4]}, HOLD={r[5]}")
    
    conn.close()

if __name__ == "__main__":
    check_signals()
