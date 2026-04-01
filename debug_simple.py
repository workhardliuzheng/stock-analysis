#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import traceback

try:
    print("步骤1: 导入IndexAnalyzer...")
    from analysis.index_analyzer import IndexAnalyzer
    print("导入成功")
    
    print("\n步骤2: 创建分析器...")
    analyzer = IndexAnalyzer('000688.SH', start_date='20230101')
    print("创建成功")
    
    print("\n步骤3: 运行分析...")
    result = analyzer.analyze(include_ml=True)
    print("分析完成")
    
except Exception as e:
    print(f"\n错误: {e}")
    traceback.print_exc()
