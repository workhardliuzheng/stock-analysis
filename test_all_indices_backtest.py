"""
测试所有8个指数的多指数组合回测
"""

import sys
sys.path.insert(0, '.')

from analysis.index_analyzer import backtest_multi_index

if __name__ == '__main__':
    print("=" * 80)
    print("测试所有8个指数的多指数组合回测")
    print("=" * 80)
    
    # 测试所有8个指数
    backtest_multi_index(
        codes=None,  # None 表示所有8个指数
        strategy='ml',
        include_ml=True,
        use_market_timing=True
    )
    
    print("\n测试完成！")
