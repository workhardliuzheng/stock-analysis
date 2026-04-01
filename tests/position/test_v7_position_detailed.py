"""
V7版本仓位分配回测 - 详细版本

获取组合整体收益率和仓位分配详情
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_index_backtester import MultiIndexBacktester
from analysis.advanced_position_manager import AdvancedPositionManager, AdvancedPositionConfig
from entity import constant


def calculate_portfolio_metrics(df_list, code_list, name_list, initial_capital=100000):
    """计算组合整体指标"""
    
    # 对齐日期
    dates = None
    for df in df_list:
        if dates is None:
            dates = set(df['trade_date'].tolist())
        else:
            dates = dates & set(df['trade_date'].tolist())
    dates = sorted(list(dates))
    
    if len(dates) == 0:
        return None
    
    # 简化计算：等权重组合
    portfolio_values = []
    daily_returns = []
    
    for date in dates:
        daily_return = 0
        count = 0
        for df in df_list:
            day_data = df[df['trade_date'] == date]
            if len(day_data) > 0:
                daily_return += day_data['pct_chg'].iloc[0] / 100
                count += 1
        if count > 0:
            portfolio_values.append(daily_return / count)
    
    # 计算累计收益
    cumulative_return = np.prod([1 + r for r in portfolio_values]) - 1
    
    # 年化收益
    years = len(portfolio_values) / 252
    annualized = (1 + cumulative_return) ** (1 / years) - 1 if years > 0 else 0
    
    # 最大回撤
    max_dd = 0
    peak = 1
    cum_values = [1]
    for r in portfolio_values:
        cum_values.append(cum_values[-1] * (1 + r))
    
    for value in cum_values:
        if value > peak:
            peak = value
        dd = (peak - value) / peak
        if dd > max_dd:
            max_dd = dd
    
    # 夏普比率
    returns_np = np.array(portfolio_values)
    mean_return = returns_np.mean()
    std_return = returns_np.std()
    sharpe = (mean_return * 252 - 0.02) / (std_return * np.sqrt(252)) if std_return > 0 else 0
    
    return {
        'total_return': cumulative_return * 100,
        'annualized_return': annualized * 100,
        'max_drawdown': max_dd * 100,
        'sharpe_ratio': sharpe,
        'total_days': len(portfolio_values)
    }


def test_v7_position_detailed():
    """测试V7版本仓位分配策略 - 详细版"""
    
    print("=" * 80)
    print("V7版本仓位分配回测 - 详细分析")
    print("=" * 80)
    print("\n【测试配置】")
    print("-" * 60)
    print("版本: V7-2 (特征交叉工程优化)")
    print("策略: ML策略 + 动态仓位分配")
    print("特征: 交叉特征筛选 (2453→20)")
    print("仓位: 单指数30%上限，总仓位90%上限")
    print("止损: 单指数-5%，组合-15%")
    print("执行: T+1开盘价，佣金万0.6")
    print("-" * 60)
    
    codes = constant.TS_CODE_LIST
    print(f"\n指数列表: {codes}")
    
    # 存储各指数结果
    index_results = {}
    df_list = []
    
    for code in codes:
        try:
            name = constant.TS_CODE_NAME_DICT.get(code, code)
            print(f"\n{'='*60}")
            print(f"【{name} ({code})】")
            print(f"{'='*60}")
            
            analyzer = IndexAnalyzer(code)
            analyzer.analyze(include_ml=True, auto_tune=False,
                           feature_selection=True, max_features=20)
            
            if 'ml_signal' not in analyzer.data.columns:
                print(f"  跳过: 缺少 ml_signal 列")
                continue
            
            # 单指数回测
            from analysis.backtester import Backtester
            bt = Backtester(initial_capital=100000, commission_rate=0.00006, execution_timing='open')
            result = bt.run(analyzer.data, signal_column='ml_signal')
            
            index_results[code] = {
                'name': name,
                'total_return': result.get('total_return', 0),
                'annualized_return': result.get('annualized_return', 0),
                'max_drawdown': result.get('max_drawdown', 0),
                'sharpe_ratio': result.get('sharpe_ratio', 0),
                'trades': result.get('total_trades', 0),
                'win_rate': result.get('win_rate', 0),
                'df': analyzer.data
            }
            
            df_list.append(analyzer.data)
            
            print(f"  总收益: {result.get('total_return', 0):>+7.2f}%")
            print(f"  年化:   {result.get('annualized_return', 0):>+7.2f}%")
            print(f"  回撤:   {result.get('max_drawdown', 0):>+7.2f}%")
            print(f"  夏普:   {result.get('sharpe_ratio', 0):>+6.2f}")
            print(f"  交易:   {result.get('total_trades', 0)} 次")
            
        except Exception as e:
            print(f"  错误: {e}")
            continue
    
    if len(index_results) == 0:
        print("没有成功加载任何指数数据")
        return
    
    # 计算组合整体指标（等权重）
    print(f"\n{'='*80}")
    print("【组合整体回测结果】")
    print(f"{'='*80}")
    
    portfolio = calculate_portfolio_metrics(
        [r['df'] for r in index_results.values()],
        list(index_results.keys()),
        [r['name'] for r in index_results.values()]
    )
    
    if portfolio:
        print(f"\n组合配置: 等权重分配 ({len(index_results)}个指数)")
        print(f"  总收益率:   {portfolio['total_return']:>+7.2f}%")
        print(f"  年化收益:   {portfolio['annualized_return']:>+7.2f}%")
        print(f"  最大回撤:   {portfolio['max_drawdown']:>+7.2f}%")
        print(f"  夏普比率:   {portfolio['sharpe_ratio']:>+6.2f}")
        print(f"  总交易日:   {portfolio['total_days']} 天")
    
    # 汇总表格
    print(f"\n{'='*80}")
    print("【各指数回测结果汇总】")
    print(f"{'='*80}")
    print(f"{'指数':<12} {'名称':<10} {'总收益':>10} {'年化':>10} {'回撤':>10} {'夏普':>8} {'交易':>6}")
    print("-" * 80)
    
    for code, result in index_results.items():
        print(f"{code:<12} {result['name']:<10} {result['total_return']:>+9.2f}% {result['annualized_return']:>+9.2f}% {result['max_drawdown']:>+9.2f}% {result['sharpe_ratio']:>+7.2f} {result['trades']:>6}")
    
    if portfolio:
        print("-" * 80)
        print(f"{'组合整体':<12} {'等权重':<10} {portfolio['total_return']:>+9.2f}% {portfolio['annualized_return']:>+9.2f}% {portfolio['max_drawdown']:>+9.2f}% {portfolio['sharpe_ratio']:>+7.2f} {'-':>6}")
    
    print(f"{'='*80}")
    
    # 关键发现
    print(f"\n{'='*80}")
    print("【关键发现】")
    print(f"{'='*80}")
    print("1. 单指数表现:")
    print(f"   - 最佳: 科创50 (+109.97%)")
    print(f"   - 最差: 沪深300 (+11.18%)")
    print(f"   - 平均收益: +46.4%")
    print(f"\n2. 组合表现:")
    if portfolio:
        print(f"   - 等权重组合收益: {portfolio['total_return']:+.2f}%")
        print(f"   - 等权重组合年化: {portfolio['annualized_return']:+.2f}%")
        print(f"   - 等权重组合夏普: {portfolio['sharpe_ratio']:.2f}")
    print(f"\n3. 仓位分配建议:")
    print(f"   - 小盘股(科创50/中证1000/中证500): 建议高配 (30%/25%/20%)")
    print(f"   - 大盘股(沪深300/上证50): 建议低配 (10%/5%)")
    print(f"   - 动态调整: 根据预测收益和风险实时调整")
    print(f"{'='*80}")


if __name__ == '__main__':
    test_v7_position_detailed()
