"""
V7版本仓位分配回测测试脚本（简化版）

基于V7版本特征交叉工程优化，测试仓位分配策略的效果
"""

import sys
sys.path.insert(0, '.')

from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_index_backtester import MultiIndexBacktester
from analysis.advanced_position_manager import AdvancedPositionManager, AdvancedPositionConfig
from entity import constant


def test_v7_position_allocation():
    """测试V7版本仓位分配策略"""
    
    print("=" * 80)
    print("V7版本仓位分配回测测试")
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
    
    # 测试1: 全部8个指数
    print("\n" + "=" * 80)
    print("【测试1】全部8个指数 + 特征交叉 + 动态仓位")
    print("=" * 80)
    
    codes = constant.TS_CODE_LIST
    print(f"指数列表: {codes}")
    
    df_list = []
    code_list = []
    name_list = []
    
    for code in codes:
        try:
            name = constant.TS_CODE_NAME_DICT.get(code, code)
            print(f"\n加载 {name} ({code})...")
            analyzer = IndexAnalyzer(code)
            analyzer.analyze(include_ml=True, auto_tune=False,
                           feature_selection=True, max_features=20)
            
            if 'ml_signal' not in analyzer.data.columns:
                print(f"  {name}: 缺少 ml_signal 列，跳过")
                continue
            
            # 检查是否有open列
            if 'open' not in analyzer.data.columns:
                print(f"  {name}: 缺少 open 列，使用 close 替代")
                analyzer.data['open'] = analyzer.data['close']
            
            df_list.append(analyzer.data)
            code_list.append(code)
            name_list.append(name)
            print(f"  {name}: 加载成功，{len(analyzer.data)} 条数据")
            
        except Exception as e:
            print(f"  {code}: 加载失败 - {e}")
            continue
    
    if len(df_list) == 0:
        print("没有成功加载任何指数数据")
        return
    
    print(f"\n成功加载 {len(df_list)} 个指数")
    
    # 创建高级仓位配置
    position_config = AdvancedPositionConfig()
    
    # 创建多指数回测器
    print("\n初始化多指数回测器...")
    mib = MultiIndexBacktester(
        initial_capital=100000,
        commission_rate=0.00006,
        advanced_config=position_config,
        execution_timing='open'
    )
    
    # 运行回测
    print("\n运行回测...")
    signal_columns = ['ml_signal'] * len(df_list)
    
    try:
        result = mib.run(
            df_list=df_list,
            code_list=code_list,
            name_list=name_list,
            signal_columns=signal_columns,
            use_ml_signals=True,
            position_config=position_config,
            use_market_timing=True,
            market_timing_index='000300.SH'
        )
        
        if 'error' in result:
            print(f"回测失败: {result['error']}")
            return
        
        # 打印结果
        print("\n" + "=" * 80)
        print("回测结果")
        print("=" * 80)
        print(f"总收益率:   {result['total_return']:>+7.1f}%")
        print(f"年化收益:   {result['annualized_return']:>+7.1f}%")
        print(f"最大回撤:   {result['max_drawdown']:>+7.1f}%")
        print(f"夏普比率:   {result['sharpe_ratio']:>+6.2f}")
        print(f"总交易日:   {result['total_days']:>7} 天")
        print(f"交易次数:   {result['total_trades']:>7} 次")
        print(f"胜率:       {result['win_rate']:>+6.1f}%")
        print(f"盈亏比:     {result['profit_factor']:>+6.2f}")
        print(f"最终资金:   {result['final_value']:>10,.0f} 元")
        print("=" * 80)
        
    except Exception as e:
        print(f"回测异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_v7_position_allocation()
