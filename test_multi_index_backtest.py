"""
测试多指数回测
"""

import sys
sys.path.insert(0, '.')

from analysis.index_analyzer import backtest_multi_index

if __name__ == '__main__':
    print("测试多指数回测...")
    
    backtest_multi_index(
        codes=['000300.SH', '399006.SZ', '000688.SH'],
        strategy='ml',
        include_ml=True
    )
    
    print("测试完成！")
