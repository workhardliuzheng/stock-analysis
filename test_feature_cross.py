"""
特征交叉回测脚本
"""

import sys
sys.path.insert(0, '.')

from analysis.index_analyzer import backtest_multi_index

if __name__ == '__main__':
    print("=" * 80)
    print("特征交叉回测 - V7-2优化")
    print("=" * 80)
    
    # 测试沪深300, 创业板指, 科创50, 中证1000, 中证500
    print("\n【测试】5个指数 - 特征交叉回测")
    print("-" * 60)
    result = backtest_multi_index(
        codes=['000300.SH', '399006.SZ', '000688.SH', '000852.SH', '000905.SH'],
        strategy='ml',
        include_ml=True,
        use_market_timing=True
    )
    
    print("\n" + "=" * 80)
    print("特征交叉回测完成！")
    print("=" * 80)
    
    # 总结对比
    print("\n【回测对比总结】")
    print("-" * 60)
    print("V6 (20特征): 组合收益 +27.9%, 年化 +5.1%, 回撤 -6.4%, 夏普 0.47")
    print("V7-2期待: 组合收益 +32.0% ~ +35.0%, 年化 +6.0% ~ +6.7%, 回撤 -5.0% ~ -6.0%, 夏普 0.50 ~ 0.60")
    print("-" * 60)
    print("预期提升:")
    print("  - 组合收益: +4.1% ~ +7.1% (+15% ~ +25%)")
    print("  - 年化收益: +0.9% ~ +1.6% (+18% ~ +31%)")
    print("  - 最大回撤: -1.4% ~ -0.4% (-22% ~ -6%)")
    print("  - 夏普比率: +0.03 ~ +0.13 (+6% ~ +28%)")
    print("-" * 60)
