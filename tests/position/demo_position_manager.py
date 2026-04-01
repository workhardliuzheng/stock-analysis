"""
仓位管理演示脚本

演示如何使用 PositionManager 进行仓位分配
"""

import sys
sys.path.insert(0, '.')

from analysis.position_manager import PositionManager, PositionConfig


def demo_position_allocation():
    """演示仓位分配"""
    print("=" * 80)
    print("仓位管理演示：多指数分散持仓")
    print("=" * 80)
    
    # 初始化仓位管理器
    pm = PositionManager()
    
    # 模拟指数信号数据
    index_signals = {
        '000300.SH': {  # 沪深300
            'signal': 'BUY',
            'confidence': 0.65,
            'predicted_return': 0.012,  # 1.2% 预期收益
            'volatility': 0.020         # 2% 波动率
        },
        '399006.SZ': {  # 创业板指
            'signal': 'BUY',
            'confidence': 0.58,
            'predicted_return': 0.025,  # 2.5% 预期收益
            'volatility': 0.035         # 3.5% 波动率
        },
        '000001.SH': {  # 上证综指
            'signal': 'HOLD',
            'confidence': 0.45,
            'predicted_return': 0.002,  # 0.2% 预期收益
            'volatility': 0.018         # 1.8% 波动率
        },
        '000688.SH': {  # 科创50
            'signal': 'BUY',
            'confidence': 0.72,
            'predicted_return': 0.038,  # 3.8% 预期收益
            'volatility': 0.045         # 4.5% 波动率
        },
        '399905.SZ': {  # 中证500
            'signal': 'BUY',
            'confidence': 0.60,
            'predicted_return': 0.022,  # 2.2% 预期收益
            'volatility': 0.030         # 3% 波动率
        },
        '000905.SZ': {  # 中证1000
            'signal': 'SELL',
            'confidence': 0.55,
            'predicted_return': -0.005, # -0.5% 预期收益
            'volatility': 0.032         # 3.2% 波动率
        },
    }
    
    print("\n原始信号数据:")
    print("-" * 80)
    for code, data in index_signals.items():
        print(f"  {code:12} | 信号: {data['signal']:4} | "
              f"置信度: {data['confidence']:.2f} | "
              f"预期收益: {data['predicted_return']*100:>+5.1f}% | "
              f"波动率: {data['volatility']*100:>+5.1f}%")
    
    # 方法1: 基础仓位分配
    print("\n[方法1] 基础仓位分配 (综合评分法)")
    print("-" * 80)
    positions1 = pm.calculate_positions(index_signals, cash_available=1.0)
    print("仓位分配结果:")
    for code, pos in sorted(positions1.items(), key=lambda x: x[1], reverse=True):
        print(f"  {code:12} | 仓位: {pos*100:>6.1f}%")
    print(f"  {'总仓位':12} | {sum(positions1.values())*100:>6.1f}%")
    
    # 方法2: 风险调整后仓位分配
    print("\n[方法2] 风险调整后仓位分配 (均值-方差优化)")
    print("-" * 80)
    positions2 = pm.calculate_risk_adjusted_positions(index_signals)
    print("仓位分配结果 (风险厌恶系数=1.0):")
    for code, pos in sorted(positions2.items(), key=lambda x: x[1], reverse=True):
        print(f"  {code:12} | 仓位: {pos*100:>6.1f}%")
    print(f"  {'总仓位':12} | {sum(positions2.values())*100:>6.1f}%")
    
    # 方法3: 保守仓位分配
    print("\n[方法3] 保守仓位分配 (提高风险厌恶系数)")
    print("-" * 80)
    # 直接修改现有 pm 的配置
    pm.config.max_position_per_index = 0.25  # 更保守的单指数上限
    positions3 = pm.calculate_risk_adjusted_positions(index_signals)
    print("仓位分配结果 (更保守配置):")
    for code, pos in sorted(positions3.items(), key=lambda x: x[1], reverse=True):
        print(f"  {code:12} | 仓位: {pos*100:>6.1f}%")
    print(f"  {'总仓位':12} | {sum(positions3.values())*100:>6.1f}%")
    
    # 空仓判断
    print("\n[空仓判断]")
    print("-" * 80)
    
    # 所有指数都为负的情况
    negative_signals = {
        '000300.SH': {
            'signal': 'HOLD',
            'confidence': 0.48,
            'predicted_return': -0.003,
            'volatility': 0.020
        },
        '399006.SZ': {
            'signal': 'SELL',
            'confidence': 0.52,
            'predicted_return': -0.008,
            'volatility': 0.035
        }
    }
    should_empty = pm.should_empty_position(negative_signals)
    print(f"所有指数预测为负: 应该空仓 = {should_empty}")
    
    # 混合情况
    mixed_signals = {
        '000300.SH': {
            'signal': 'BUY',
            'confidence': 0.60,
            'predicted_return': 0.015,
            'volatility': 0.020
        },
        '399006.SZ': {
            'signal': 'SELL',
            'confidence': 0.55,
            'predicted_return': -0.005,
            'volatility': 0.035
        }
    }
    should_empty = pm.should_empty_position(mixed_signals)
    print(f"混合信号情況: 应该空仓 = {should_empty}")
    
    # 组合回测示例
    print("\n[组合回测示例]")
    print("-" * 80)
    print("假设 initial_capital = 100,000 元")
    print(f"使用 [方法2] 仓位分配:")
    
    initial_capital = 100000
    for code, pos in positions2.items():
        amount = initial_capital * pos
        print(f"  {code:12} | 投资金额: {amount:>10,.0f} 元")
    
    # 如果有一个指数上涨 2%
    print("\n假设科创50上涨 2%，其他不变:")
    profit = positions2.get('000688.SH', 0) * initial_capital * 0.02
    print(f"  创投50收益: {profit:>10,.2f} 元")
    
    # 如果全部指数平均上涨 1.5%
    avg_return = sum(p * r for p, r in [(positions2.get(code, 0), data['predicted_return']) 
                                        for code, data in index_signals.items()])
    total_return = sum(positions2.values()) * initial_capital * 0.015
    print(f"  预期组合收益: {total_return:>10,.2f} 元")
    
    print("\n" + "=" * 80)
    print("演示完成！")
    print("=" * 80)


if __name__ == '__main__':
    demo_position_allocation()
