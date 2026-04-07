#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
回测2021-2022年熊市期间表现

测试策略能否在过去熊市中保护资产
"""

import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from datetime import datetime
from analysis.index_analyzer import IndexAnalyzer, Backtester
from entity import constant


def backtest_bear_market():
    """回测2021-2022年熊市期间表现"""
    print("=" * 70)
    print("[OK] 2021-2022年熊市期间策略回测")
    print("=" * 70)
    print("\n测试时间范围: 2021-01-01 ~ 2022-12-31")
    
    # 关键指数（2021-2022年表现差）
    test_indices = {
        '000688.SH': '科创50',      # 科创板，2021-2022年大跌
        '399006.SZ': '创业板指',    # 创业板，2021-2022年大跌
        '000001.SH': '上证综指',    # 大盘指数
        '000300.SH': '沪深300',     # 蓝筹指数
    }
    
    # 策略配置
    strategies = {
        '多因子策略': 'factor_signal',
        '混合策略': 'final_signal',
    }
    
    results = []
    
    for code, name in test_indices.items():
        try:
            print(f"\n{'='*70}")
            print(f"回测: {name} ({code})")
            print(f"{'='*70}")
            
            # 加载数据（指定时间范围）
            analyzer = IndexAnalyzer(code, start_date='20210101')
            analyzer.analyze(include_ml=False, auto_tune=False)  # 不用ML避免数据泄露
            
            # 过滤日期范围（因为IndexAnalyzer不支持end_date参数）
            analyzer.data = analyzer.data[
                (analyzer.data['trade_date'] >= '2021-01-01') & 
                (analyzer.data['trade_date'] <= '2022-12-31')
            ]
            
            print(f"数据范围: {analyzer.data['trade_date'].min()} ~ {analyzer.data['trade_date'].max()}")
            print(f"数据条数: {len(analyzer.data)}")
            
            # 运行回测
            bt = Backtester(commission_rate=0.00006, execution_timing='close')
            
            for strategy_name, signal_col in strategies.items():
                if signal_col in analyzer.data.columns:
                    result = bt.run(analyzer.data, signal_col)
                    results.append({
                        '指数': name,
                        '代码': code,
                        '策略': strategy_name,
                        '总收益': result.get('total_return', 0) * 100,
                        '夏普比率': result.get('sharpe_ratio', 0),
                        '最大回撤': result.get('max_drawdown', 0),
                        '收益回撤比': result.get('total_return', 0) / abs(result.get('max_drawdown', 0.01)) if result.get('max_drawdown', 0) != 0 else 0,
                    })
                    print(f"\n[OK] {strategy_name}:")
                    print(f"  总收益: {result.get('total_return', 0) * 100:+.2f}%")
                    print(f"  夏普比率: {result.get('sharpe_ratio', 0):.4f}")
                    print(f"  最大回撤: {result.get('max_drawdown', 0)*100:+.2f}%")
                    print(f"  收益回撤比: {result.get('total_return', 0) / abs(result.get('max_drawdown', 0.01)):0.2f}")
                else:
                    print(f"[WARNING] {signal_col} 列不存在")
            
            # 基准（买入持有）
            print(f"\n[基准] 买入持有:")
            buy_hold = (analyzer.data['close'].iloc[-1] - analyzer.data['close'].iloc[0]) / analyzer.data['close'].iloc[0]
            print(f"  总收益: {buy_hold*100:+.2f}%")
            
        except Exception as e:
            print(f"[ERROR] {name} 回测失败: {e}")
    
    # 输出汇总
    print("\n" + "=" * 70)
    print("[OK] 汇总结果（2021-2022年熊市）")
    print("=" * 70)
    print(f"{'指数':<10} {'策略':<15} {'总收益':<12} {'夏普比率':<12} {'最大回撤':<12} {'收益/回撤':<12}")
    print("-" * 70)
    
    for r in sorted(results, key=lambda x: (x['指数'], x['策略'])):
        print(f"{r['指数']:<10} {r['策略']:<15} {r['总收益']:>+11.2f}% {r['夏普比率']:>11.4f} {r['最大回撤']:>+11.2f}% {r['收益回撤比']:>+11.2f}")
    
    print("=" * 70)
    
    # 关键问题：策略能否跑赢买入持有？
    print("\n[OK] 关键问题：策略能否跑赢买入持有？")
    print()
    
    for code, name in test_indices.items():
        index_results = [r for r in results if r['代码'] == code]
        if index_results:
            best_strategy = max(index_results, key=lambda x: x['总收益'])
            print(f"{name}:")
            print(f"  策略收益: {best_strategy['总收益']:+.2f}%")
            
            # 获取基准收益
            try:
                analyzer = IndexAnalyzer(code, start_date='20210101')
                # 过滤日期范围
                analyzer.data = analyzer.data[
                    (analyzer.data['trade_date'] >= '2021-01-01') & 
                    (analyzer.data['trade_date'] <= '2022-12-31')
                ]
                buy_hold = (analyzer.data['close'].iloc[-1] - analyzer.data['close'].iloc[0]) / analyzer.data['close'].iloc[0]
                print(f"  基准收益: {buy_hold*100:+.2f}%")
                if best_strategy['总收益'] > buy_hold * 100:
                    print(f"  [OK] 超越基准 {best_strategy['总收益'] - buy_hold*100:+.2f}%")
                else:
                    print(f"  [WARNING] 未超越基准 {best_strategy['总收益'] - buy_hold*100:+.2f}%")
            except:
                print(f"  [WARNING] 无法计算基准")
            print()


if __name__ == "__main__":
    backtest_bear_market()
