import traceback
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("步骤1: 导入模块...")
    from analysis.index_analyzer import IndexAnalyzer
    import pandas as pd
    import numpy as np
    print("导入成功")
    
    print("\n步骤2: 创建分析器...")
    analyzer = IndexAnalyzer('000688.SH', start_date='20230101')
    print("分析器创建成功")
    
    print("\n步骤3: 运行分析...")
    result = analyzer.analyze(include_ml=True)
    print(f"分析完成")
    print(f"结果类型: {type(result)}")
    if isinstance(result, dict):
        print(f"结果键: {result.keys()}")
        if 'data' in result:
            print(f"数据行数: {len(result['data'])}")
            print(f"列: {result['data'].columns.tolist()}")
    
except Exception as e:
    print(f"\n错误: {e}")
    traceback.print_exc()
