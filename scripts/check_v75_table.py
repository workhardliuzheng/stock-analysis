#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查数据库表是否存在"""

from mysql_connect.db import get_engine
from sqlalchemy import text

engine = get_engine()

try:
    with engine.connect() as conn:
        # 检查表是否存在
        result = conn.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'ts_stock_data' 
            AND table_name = 'v75_optimal_weights'
        """))
        exists = result.scalar()
        print(f"v75_optimal_weights 表存在: {exists > 0}")
        
        if exists == 0:
            print("正在创建表...")
            conn.execute(text("""
                CREATE TABLE v75_optimal_weights (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    ts_code VARCHAR(20) NOT NULL UNIQUE,
                    name VARCHAR(50) NOT NULL,
                    factor_score DECIMAL(10,4) NOT NULL,
                    factor_signal DECIMAL(10,4) NOT NULL,
                    ml_return DECIMAL(10,4) NOT NULL,
                    ml_signal DECIMAL(10,4) NOT NULL,
                    best_sharpe DECIMAL(10,4) NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """))
            print("表创建成功!")
        else:
            print("表已存在，测试插入...")
            conn.execute(text("""
                INSERT INTO v75_optimal_weights (ts_code, name, factor_score, factor_signal, ml_return, ml_signal, best_sharpe)
                VALUES ('TEST001', '测试', 0.5, 0.2, 0.2, 0.1, 1.5)
                ON DUPLICATE KEY UPDATE name = VALUES(name)
            """))
            print("测试插入成功!")
            conn.execute(text("DELETE FROM v75_optimal_weights WHERE ts_code = 'TEST001'"))
            print("测试清理完成!")
            
except Exception as e:
    print(f"错误: {e}")
