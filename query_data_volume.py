#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查询数据库中指数数据量"""

import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from mysql_connect.db import get_engine
from sqlalchemy import text

def query_data_volume():
    """查询各指数数据量"""
    engine = get_engine()
    
    query = """
    SELECT 
        ts_code,
        COUNT(*) as cnt,
        MIN(trade_date) as min_date,
        MAX(trade_date) as max_date,
        TIMESTAMPDIFF(DAY, MIN(trade_date), MAX(trade_date)) as days
    FROM ts_stock_data
    WHERE ts_code IN ('399001.SZ', '399006.SZ', '000001.SH', '000300.SH', '000688.SH', '000852.SH', '000905.SH', '000016.SH')
    GROUP BY ts_code
    ORDER BY ts_code
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(query))
        print("=" * 100)
        print("指数数据量统计")
        print("=" * 100)
        print(f"{'指数代码':<12} {'数据量':>8} {'最早日期':>10} {'最近日期':>10} {'天数':>6} {'年数':>6}")
        print("-" * 100)
        
        total_days = 0
        total_rows = 0
        
        for row in result:
            ts_code, cnt, min_date, max_date, days = row
            years = round(days / 365, 2)
            total_days += days
            total_rows += cnt
            print(f"{ts_code:<12} {cnt:>8} {min_date} {max_date} {days:>6} {years:>6.2f}")
        
        print("-" * 100)
        avg_days = total_days / 8 if total_days > 0 else 0
        print(f"{'总计':<12} {total_rows:>8} {'-':>10} {'-':>10} {total_days:>6} {round(avg_days/365, 2):>6.2f} 平均")
        print("=" * 100)
        
        print("\n建议分析:")
        if avg_days < 1800:  # 少于5年
            print("⚠️  数据量较少（平均<5年），建议同步更长时间数据以提升ML模型训练效果")
            print("   推荐至少5年数据（约1200-1500条）用于Walk-Forward训练")
        elif avg_days < 2500:  # 少于7年
            print("✓  数据量适中（5-7年），可以进行基本分析")
        else:
            print("✓✓ 数据量充足（>7年），适合进行深度ML训练")
        
        print("\n当前配置的历史起始日期:")
        print("  - 大部分指数: 2015-01-01 (约9年数据)")
        print("  - 沪深300: 2017-01-01 (约7年数据)")
        print("  - 科创50: 2020-07-01 (约6年数据)")
        print("  - 上证50: 2012-01-01 (约12年数据)")

if __name__ == "__main__":
    query_data_volume()
