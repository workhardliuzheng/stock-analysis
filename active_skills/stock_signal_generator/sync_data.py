#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股市分析系统 - 数据同步模块

功能: 从Tushare同步指数数据到本地
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer

def sync_data(indices, start_date, tushare_token):
    """同步指数数据"""
    results = {}
    
    # 临时更新Tushare token
    import os
    os.environ['TUSHARE_TOKEN'] = tushare_token
    
    for code in indices:
        try:
            print(f"正在同步 {code}...")
            
            analyzer = IndexAnalyzer(
                ts_code=code,
                start_date=start_date
            )
            result = analyzer.analyze(include_ml=False)
            
            if result is not None and len(result) > 0:
                results[code] = len(result)
                print(f"  [OK] {code} - 成功加载 {len(result)} 行数据")
            else:
                print(f"  [WARNING] {code} - 数据为空")
                
        except Exception as e:
            print(f"  [ERROR] {code} - 出错: {str(e)}")
    
    return results

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='数据同步')
    parser.add_argument('--tushare-token', required=True, help='Tushare Pro API Token')
    parser.add_argument('--indices', default='000688.SH,399006.SZ,000001.SH,000905.SH,000852.SH', help='指数代码')
    parser.add_argument('--start-date', default='20230101', help='起始日期')
    
    args = parser.parse_args()
    
    indices = [idx.strip() for idx in args.indices.split(',')]
    
    results = sync_data(indices, args.start_date, args.tushare_token)
    
    print("\n同步结果:")
    for code, rows in results.items():
        print(f"  {code}: {rows} 行")
