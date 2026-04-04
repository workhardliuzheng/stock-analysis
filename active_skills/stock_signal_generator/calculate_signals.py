#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股市分析系统 - 信号计算模块

功能: 计算多因子信号、ML信号、融合信号
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.multi_factor_scorer import MultiFactorScorer
from analysis.signal_threshold_optimizer import get_aggressive_lite_threshold_optimizer
from analysis.adaptive_fusion_optimizer import MetaLearner

def calculate_signals(indices, start_date, tushare_token):
    """计算信号"""
    from analysis.index_analyzer import IndexAnalyzer
    
    results = {}
    
    for code in indices:
        try:
            print(f"正在计算 {code} 的信号...")
            
            # 1. 加载数据
            # 临时设置Tushare token
            os.environ['TUSHARE_TOKEN'] = tushare_token
            
            analyzer = IndexAnalyzer(
                ts_code=code,
                start_date=start_date
            )
            data = analyzer.analyze(include_ml=True)
            
            if data is None or len(data) == 0:
                print(f"  [WARNING] {code} - 数据为空")
                continue
            
            # 2. 计算多因子评分
            scorer = MultiFactorScorer()
            df = scorer.calculate(data)
            
            # 3. 应用V7-4信号阈值优化
            optimizer = get_aggressive_lite_threshold_optimizer()
            new_signals = []
            for i in range(len(df)):
                row = df.iloc[i]
                score = row['factor_score']
                trend_state = row['trend_state']
                signal, _ = optimizer.generate_signal(score, trend_state)
                new_signals.append(signal)
            
            df['v74_signal'] = new_signals
            
            # 4. 计算统计信息
            signal_counts = df['v74_signal'].value_counts()
            
            results[code] = {
                'total_rows': len(df),
                'buy_signals': signal_counts.get('BUY', 0),
                'sell_signals': signal_counts.get('SELL', 0),
                'hold_signals': signal_counts.get('HOLD', 0),
            }
            
            print(f"  [OK] {code} - BUY={signal_counts.get('BUY', 0)}, SELL={signal_counts.get('SELL', 0)}, HOLD={signal_counts.get('HOLD', 0)}")
            
        except Exception as e:
            print(f"  [ERROR] {code} - 出错: {str(e)}")
    
    return results

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='信号计算')
    parser.add_argument('--tushare-token', required=True, help='Tushare Pro API Token')
    parser.add_argument('--indices', default='000688.SH,399006.SZ,000001.SH,000905.SH,000852.SH', help='指数代码')
    parser.add_argument('--start-date', default='20230101', help='起始日期')
    
    args = parser.parse_args()
    
    indices = [idx.strip() for idx in args.indices.split(',')]
    
    results = calculate_signals(indices, args.start_date, args.tushare_token)
    
    print("\n信号结果:")
    for code, stats in results.items():
        total = stats['total_rows']
        print(f"  {code}: BUY={stats['buy_signals']} ({stats['buy_signals']/total*100:.1f}%), SELL={stats['sell_signals']} ({stats['sell_signals']/total*100:.1f}%), HOLD={stats['hold_signals']} ({stats['hold_signals']/total*100:.1f}%)")
