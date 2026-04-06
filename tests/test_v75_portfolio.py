#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V7-5 组合回测验证

测试V7-5自适应融合优化在8个指数上的效果
"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_factor_scorer import MultiFactorScorer
from analysis.adaptive_fusion_optimizer import MetaLearner

# 5个指数配置
INDEX_PORTFOLIO = {
    '000688.SH': {'name': '科创50', 'weight': 0.20},
    '399006.SZ': {'name': '创业板指', 'weight': 0.20},
    '000001.SH': {'name': '上证综指', 'weight': 0.20},
    '000905.SH': {'name': '中证500', 'weight': 0.20},
    '000852.SH': {'name': '中证1000', 'weight': 0.20},
}

print("="*80)
print("V7-5 自适应融合优化 - 组合回测")
print("="*80)

# 1. 加载所有指数数据
print("\n[步骤1] 加载指数数据...")
index_data = {}

for code, info in INDEX_PORTFOLIO.items():
    print(f"  正在加载 {info['name']:>8} ({code})...")
    
    analyzer = IndexAnalyzer(code, start_date='20230101')
    result = analyzer.analyze(include_ml=False)
    
    if result is not None and len(result) > 0:
        # 计算多因子评分
        scorer = MultiFactorScorer()
        df = scorer.calculate(result)
        
        index_data[code] = {
            'data': df,
            'name': info['name'],
            'weight': info['weight'],
        }
        print(f"    [OK] 加载成功 ({len(df)} 行)")
    else:
        print(f"    [ERROR] 加载失败")

if len(index_data) == 0:
    print("[ERROR] 没有成功加载的数据")
    sys.exit(1)

# 2. 找到共同日期
print("\n[步骤2] 找到共同日期...")
common_dates = None
for code, info in index_data.items():
    df = info['data']
    if common_dates is None:
        common_dates = set(df.index)
    else:
        common_dates = common_dates & set(df.index)

common_dates = sorted(list(common_dates))
print(f"[OK] 共同日期数: {len(common_dates)}")

# 3. 计算V7-5最优权重
print("\n[步骤3] 计算V7-5最优权重...")

# 合并所有指数数据
all_data_list = []
for code, info in index_data.items():
    df = info['data'].loc[common_dates].copy()
    df['index_code'] = code
    all_data_list.append(df)

combined_df = pd.concat(all_data_list, ignore_index=True)

# 创建MetaLearner
meta_learner = MetaLearner(
    initial_train_size=300,
    test_size=60,
    max_trials=10,
    market_state='oscillation'
)

# 确保信号列为数值
combined_df['factor_signal_num'] = combined_df['factor_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)

# 计算ml_predicted_return (简化: 用factor_score变化率作为代理)
combined_df['ml_predicted_return'] = combined_df.groupby('index_code')['factor_score'].diff().fillna(0) / 10

# 优化
weights, sharpe = meta_learner.optimize(combined_df)

print(f"\n{'='*80}")
print("[OK] V7-5 组合优化完成")
print(f"{'='*80}")
print(f"  最优夏普比率: {sharpe:.4f}")
print(f"  权重分配:")
for key, value in weights.items():
    print(f"    {key}: {value:.2%}")

# 4. 生成融合信号
print("\n[步骤4] 生成融合信号...")

# 重置索引
combined_df = combined_df.reset_index(drop=True)
combined_df['ml_signal_num'] = combined_df['factor_signal_num'].copy()  # 临时替代

df_fused = meta_learner.generate_fused_signal(combined_df)

# 5. 计算组合收益
print("\n[步骤5] 计算组合收益...")

# 按指数加权
portfolio_return = 0.0
total_weight = 0.0

for code, info in index_data.items():
    weight = info['weight']
    
    # 获取该指数的融合信号
    df_index = df_fused[df_fused['index_code'] == code].copy()
    
    if len(df_index) > 0:
        # 计算加权信号
        df_index['position'] = np.sign(df_index['fused_score'] - 50)
        df_index['strategy_return'] = df_index['position'] * df_index['pct_chg'] / 100
        
        # 累加
        portfolio_return += df_index['strategy_return'].sum() * weight
        total_weight += weight

print(f"\n{'='*80}")
print("[OK] 组合回测结果")
print(f"{'='*80}")
print(f"  组合总收益: {portfolio_return * 100:.2f}%")
print(f"  总权重: {total_weight:.2f} (目标: 1.0)")

# 6. 原始多因子策略对比
print("\n[步骤6] 原始多因子策略对比...")

orig_return = 0.0

for code, info in index_data.items():
    weight = info['weight']
    df = info['data'].loc[common_dates].copy()
    
    if len(df) > 0:
        # 原始信号 (factor_score >= 60 BUY, < 40 SELL)
        df['position'] = df['factor_score'].apply(lambda x: 1.0 if x >= 60 else (-1.0 if x < 40 else 0.0))
        df['strategy_return'] = df['position'] * df['pct_chg'] / 100
        
        orig_return += df['strategy_return'].sum() * weight

print(f"\n{'='*80}")
print("[OK] 最终对比")
print(f"{'='*80}")
print(f"\n原始多因子策略:")
print(f"  组合总收益: {orig_return * 100:.2f}%")

print(f"\nV7-5自适应融合策略:")
print(f"  组合总收益: {portfolio_return * 100:.2f}% {'[↑ 更优]' if portfolio_return > orig_return else '[↓ 较差]'}")

print(f"\n收益提升:")
improvement = ((portfolio_return - orig_return) / abs(orig_return) * 100) if orig_return != 0 else 0
print(f"  相对提升: {improvement:+.2f}%")
