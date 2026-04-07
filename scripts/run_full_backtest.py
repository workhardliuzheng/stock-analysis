#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
-full backtest script with stop loss
Full backtest with stop loss and all strategies
"""

import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer, Backtester
from entity import constant


def full_backtest(indices, strategy='all', start_date='20210101', end_date='20230101'):
    """
    完整回测（支持止损）
    
    Args:
        indices: 指数列表 [(code, name)]
        strategy: 'all' 或具体策略名
        start_date: 开始日期
        end_date: 结束日期
    """
    print("=" * 80)
    print(" [FULL BACKTEST] 完整回测（含止损机制）")
    print("=" * 80)
    print(f"\n时间范围: {start_date} ~ {end_date}")
    print(f"策略: {strategy}")
    
    results = []
    
    for code, name in indices:
        try:
            print(f"\n{'='*80}")
            print(f" 回测: {name} ({code})")
            print(f"{'='*80}")
            
            # 加载并分析数据
            analyzer = IndexAnalyzer(code, start_date=start_date)
            analyzer.analyze(include_ml=(strategy in ['all', 'ml', 'combined']), auto_tune=False)
            
            # 过滤日期范围
            analyzer.data = analyzer.data[
                (analyzer.data['trade_date'] >= start_date) & 
                (analyzer.data['trade_date'] <= end_date)
            ]
            
            print(f"\n[OK] 数据范围: {analyzer.data['trade_date'].min()} ~ {analyzer.data['trade_date'].max()}")
            print(f"[OK] 数据条数: {len(analyzer.data)}")
            
            # 检查信号分布
            if 'final_signal' in analyzer.data.columns:
                print(f"\n[OK] final_signal 分布:")
                signal_counts = analyzer.data['final_signal'].value_counts()
                for sig, count in signal_counts.items():
                    print(f"  {sig}: {count} ({count/len(analyzer.data)*100:.1f}%)")
            
            if 'final_signal_stop' in analyzer.data.columns:
                print(f"\n[OK] final_signal_stop 分布 (含止损):")
                signal_counts = analyzer.data['final_signal_stop'].value_counts()
                for sig, count in signal_counts.items():
                    print(f"  {sig}: {count} ({count/len(analyzer.data)*100:.1f}%)")
            
            # 运行回测
            bt = Backtester(commission_rate=0.00006, execution_timing='close')
            
            # 测试所有信号列
            signal_columns = ['final_signal', 'final_signal_stop']
            
            if strategy == 'all':
                strategies_to_test = ['factor_signal', 'ml_signal', 'final_signal', 'final_signal_stop']
            else:
                strategies_to_test = [strategy + '_signal', strategy + '_signal_stop']
            
            for signal_col in signal_columns:
                if signal_col not in analyzer.data.columns:
                    continue
                
                print(f"\n[BACKTEST] 测试信号: {signal_col}")
                
                # 过滤其实信号
                strategy_signals = analyzer.data[analyzer.data[signal_col].isin(['BUY', 'SELL', 'HOLD'])].copy()
                
                if len(strategy_signals) < 10:
                    print(f"  [WARNING] 信号数据太少 ({len(strategy_signals)} 条)，跳过")
                    continue
                
                result = bt.run(strategy_signals, signal_col)
                
                if result:
                    results.append({
                        '指数': name,
                        '代码': code,
                        '信号': signal_col,
                        '策略': signal_col.replace('_signal', ''),
                        '总收益': result.get('total_return', 0) * 100,
                        '夏普比率': result.get('sharpe_ratio', 0),
                        '最大回撤': result.get('max_drawdown', 0),
                        '收益回撤比': result.get('total_return', 0) / abs(result.get('max_drawdown', 0.01)) if result.get('max_drawdown', 0) != 0 else 0,
                        '交易次数': result.get('trades', 0),
                    })
                    
                    print(f"  [OK] 总收益: {result.get('total_return', 0) * 100:+.2f}%")
                    print(f"  [OK] 夏普比率: {result.get('sharpe_ratio', 0):.4f}")
                    print(f"  [OK] 最大回撤: {result.get('max_drawdown', 0)*100:+.2f}%")
                    print(f"  [OK] 收益/回撤: {result.get('total_return', 0) / abs(result.get('max_drawdown', 0.01)):0.2f}")
                    print(f"  [OK] 交易次数: {result.get('trades', 0)}")
            
            # 基准（买入持有）
            print(f"\n[基准] 买入持有:")
            buy_hold = (analyzer.data['close'].iloc[-1] - analyzer.data['close'].iloc[0]) / analyzer.data['close'].iloc[0]
            print(f"  总收益: {buy_hold*100:+.2f}%")
            
            # 最优策略对比
            index_results = [r for r in results if r['代码'] == code]
            if index_results:
                best_result = max(index_results, key=lambda x: x['总收益'])
                if best_result['总收益'] > buy_hold * 100:
                    print(f"\n[OK] 最优策略 '{best_result['信号']}' 超越基准 {best_result['总收益'] - buy_hold*100:+.2f}%")
                else:
                    print(f"\n[WARNING] 最优策略 '{best_result['信号']}' 未超越基准 {best_result['总收益'] - buy_hold*100:+.2f}%")
        
        except Exception as e:
            print(f"\n[ERROR] {name} 回测失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 输出汇总
    print("\n" + "=" * 80)
    print(" [OK] 汇总结果")
    print("=" * 80)
    print(f"{'指数':<10} {'信号':<20} {'总收益':<12} {'夏普比率':<12} {'最大回撤':<12} {'收益/回撤':<12}")
    print("-" * 80)
    
    for r in sorted(results, key=lambda x: (x['指数'], x['信号'])):
        print(f"{r['指数']:<10} {r['信号']:<20} {r['总收益']:>+11.2f}% {r['夏普比率']:>11.4f} {r['最大回撤']:>+11.2f}% {r['收益回撤比']:>+11.2f}")
    
    print("=" * 80)
    
    # 关键问题：策略能否跑赢买入持有？
    print("\n[OK] 关键问题：策略能否跑赢买入持有？")
    print()
    
    for code, name in indices:
        index_results = [r for r in results if r['代码'] == code]
        if index_results:
            best_strategy = max(index_results, key=lambda x: x['总收益'])
            print(f"{name}:")
            print(f"  最优策略: {best_strategy['信号']}")
            print(f"  策略收益: {best_strategy['总收益']:+.2f}%")
            
            # 获取基准收益
            try:
                analyzer = IndexAnalyzer(code, start_date=start_date)
                analyzer.data = analyzer.data[
                    (analyzer.data['trade_date'] >= start_date) & 
                    (analyzer.data['trade_date'] <= end_date)
                ]
                buy_hold = (analyzer.data['close'].iloc[-1] - analyzer.data['close'].iloc[0]) / analyzer.data['close'].iloc[0]
                print(f"  基准收益: {buy_hold*100:+.2f}%")
                if best_strategy['总收益'] > buy_hold * 100:
                    print(f"  [OK] 超越基准 {best_strategy['总收益'] - buy_hold*100:+.2f}%")
                else:
                    print(f"  [WARNING] 未超越基准 {best_strategy['总收益'] - buy_hold*100:+.2f}%")
            except Exception as e:
                print(f"  [WARNING] 无法计算基准: {e}")
            print()


if __name__ == "__main__":
    # 测试近5年（2019-2024）
    indices = [
        ('000688.SH', '科创50'),
        ('399006.SZ', '创业板指'),
        ('000001.SH', '上证综指'),
        ('000300.SH', '沪深300'),
        ('399001.SZ', '深证成指'),
        ('000852.SH', '中证1000'),
        ('000905.SH', '中证500'),
        ('000016.SH', '上证50'),
    ]
    
    # 运行回测
    full_backtest(indices, strategy='all', start_date='20190101', end_date='20241231')
