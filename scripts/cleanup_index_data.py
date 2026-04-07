#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清理指数数据脚本
删除所有指数数据，以便重新从历史起始日期同步
"""

import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from mysql_connect.db import get_engine
from sqlalchemy import text

def cleanup_index_data():
    """清理指数数据"""
    engine = get_engine()
    
    # 删除所有指数数据
    delete_query = "DELETE FROM ts_stock_data WHERE ts_code IN ('399001.SZ', '399006.SZ', '000001.SH', '000300.SH', '000688.SH', '000852.SH', '000905.SH', '000016.SH')"
    
    with engine.connect() as conn:
        # 开启事务
        trans = conn.begin()
        try:
            result = conn.execute(text(delete_query))
            print(f"[OK] 删除了 {result.rowcount} 条指数数据")
            
            # 检查剩余数据
            check_query = "SELECT COUNT(*) as cnt FROM ts_stock_data"
            result = conn.execute(text(check_query))
            count = result.fetchone()[0]
            print(f"[INFO] 当前剩余数据: {count} 条")
            
            trans.commit()
            print("[OK] 清理完成")
        except Exception as e:
            trans.rollback()
            print(f"[ERROR] 清理失败: {str(e)}")

if __name__ == "__main__":
    cleanup_index_data()
