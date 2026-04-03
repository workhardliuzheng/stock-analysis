#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股市分析系统 - 信号生成主程序

功能:
1. 同步增量数据
2. 计算多因子信号
3. 计算ML预测信号
4. 融合生成最终信号
5. 保存结果

使用方法:
    python run_signal_generator.py --tushare-token YOUR_TOKEN [--data-only] [--signal-only]

参数:
    --tushare-token: Tushare Pro API Token (必需)
    --data-only: 仅执行数据同步
    --signal-only: 仅执行信号计算
    --indices: 指定指数代码 (逗号分隔)
    --start-date: 数据起始日期 (默认: 20230101)
"""
import sys
import os
import argparse
import logging
from datetime import datetime

# 添加项目路径
sys.path.insert(0, r'E:\pycharm\stock-analysis')

# 导入项目模块
from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_factor_scorer import MultiFactorScorer
from analysis.signal_threshold_optimizer import get_aggressive_lite_threshold_optimizer
from analysis.adaptive_fusion_optimizer import MetaLearner

# 配置日志
def setup_logging():
    """配置日志输出"""
    log_dir = r'E:\pycharm\stock-analysis\logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建logger
    logger = logging.getLogger('signal_generator')
    logger.setLevel(logging.DEBUG)
    
    # 文件handler
    file_handler = logging.FileHandler(
        os.path.join(log_dir, f'run_{datetime.now().strftime("%Y%m%d")}.log'),
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # 格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # 添加handler
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()

# 默认指数配置
DEFAULT_INDICES = [
    '000688.SH',  # 科创50
    '399006.SZ',  # 创业板指
    '000001.SH',  # 上证综指
    '000905.SH',  # 中证500
    '000852.SH',  # 中证1000
]

def sync_data(indices, start_date, tushare_token):
    """同步数据"""
    logger.info(f"[数据同步] 开始同步数据")
    
    results = {}
    
    for code in indices:
        try:
            logger.info(f"[数据同步] 正在同步 {code}...")
            
            analyzer = IndexAnalyzer(
                index_code=code,
                start_date=start_date,
                tushare_token=tushare_token
            )
            result = analyzer.analyze(include_ml=False)
            
            if result is not None and len(result) > 0:
                results[code] = len(result)
                logger.info(f"[数据同步] {code} - 成功加载 {len(result)} 行数据")
            else:
                logger.warning(f"[数据同步] {code} - 数据为空")
                
        except Exception as e:
            logger.error(f"[数据同步] {code} - 出错: {str(e)}")
    
    return results

def calculate_signals(indices, start_date, tushare_token):
    """计算信号"""
    logger.info(f"[信号计算] 开始计算信号")
    
    results = {}
    
    for code in indices:
        try:
            logger.info(f"[信号计算] 正在计算 {code} 的信号...")
            
            # 1. 加载数据
            analyzer = IndexAnalyzer(
                index_code=code,
                start_date=start_date,
                tushare_token=tushare_token
            )
            data = analyzer.analyze(include_ml=True)
            
            if data is None or len(data) == 0:
                logger.warning(f"[信号计算] {code} - 数据为空")
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
            
            logger.info(f"[信号计算] {code} - BUY={signal_counts.get('BUY', 0)}, SELL={signal_counts.get('SELL', 0)}, HOLD={signal_counts.get('HOLD', 0)}")
            
        except Exception as e:
            logger.error(f"[信号计算] {code} - 出错: {str(e)}")
    
    return results

def generate_full_report(indices, start_date, tushare_token):
    """生成完整报告"""
    logger.info(f"[完整报告] 开始生成完整报告")
    
    results = {
        'data_sync': {},
        'signal_calculate': {},
        'fusion': {},
    }
    
    for code in indices:
        try:
            logger.info(f"[完整报告] 正在处理 {code}...")
            
            # 1. 加载数据
            analyzer = IndexAnalyzer(
                index_code=code,
                start_date=start_date,
                tushare_token=tushare_token
            )
            data = analyzer.analyze(include_ml=True)
            
            if data is None or len(data) == 0:
                continue
            
            # 2. 计算多因子评分
            scorer = MultiFactorScorer()
            df = scorer.calculate(data)
            
            # 3. 训练ML模型
            from analysis.ml_predictor import MLPredictor
            predictor = MLPredictor()
            df, metrics = predictor.train_and_predict(df, auto_tune=False)
            
            # 4. 应用V7-4信号阈值优化
            from analysis.signal_threshold_optimizer import get_aggressive_lite_threshold_optimizer
            optimizer = get_aggressive_lite_threshold_optimizer()
            new_signals = []
            for i in range(len(df)):
                row = df.iloc[i]
                score = row['factor_score']
                trend_state = row['trend_state']
                signal, _ = optimizer.generate_signal(score, trend_state)
                new_signals.append(signal)
            
            df['v74_signal'] = new_signals
            
            # 5. 应用V7-5融合优化
            df['factor_signal_num'] = df['v74_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)
            df['ml_predicted_return'] = df['ml_predicted_return'].fillna(0)
            
            meta_learner = MetaLearner(market_state='oscillation')
            # 临时设置默认权重
            meta_learner.best_weights = {
                'factor_score': 0.7358,
                'factor_signal': 0.0394,
                'ml_return': 0.1679,
                'ml_signal': 0.0568,
            }
            
            df = meta_learner.generate_fused_signal(df)
            
            # 6. 计算最终信号统计
            final_signals = df['fused_signal'].value_counts()
            
            # 7. 计算回测收益
            df['position'] = df['fused_score'].apply(
                lambda x: 1.0 if x >= 60 else (-1.0 if x < 40 else 0.0)
            )
            df['strategy_return'] = df['position'] * df['pct_chg'] / 100
            
            cumulative_return = (1 + df['strategy_return']).cumprod() - 1
            total_return = cumulative_return.iloc[-1] * 100
            
            if df['strategy_return'].std() > 0:
                sharpe = df['strategy_return'].mean() / df['strategy_return'].std() * 252**0.5
            else:
                sharpe = 0.0
            
            results['fusion'][code] = {
                'buy_signals': final_signals.get('BUY', 0),
                'sell_signals': final_signals.get('SELL', 0),
                'hold_signals': final_signals.get('HOLD', 0),
                'total_return': total_return,
                'sharpe_ratio': sharpe,
            }
            
            logger.info(f"[完整报告] {code} - 收益: {total_return:.2f}%, 夏普: {sharpe:.4f}")
            
        except Exception as e:
            logger.error(f"[完整报告] {code} - 出错: {str(e)}")
    
    return results

def print_report(data_results, signal_results, fusion_results):
    """打印报告"""
    print("\n" + "="*60)
    print("📈 股市分析系统 - 信号生成报告")
    print("="*60)
    
    print("\n✅ [数据同步]")
    if data_results:
        for code, rows in data_results.items():
            print(f"   - {code}: {rows} 行数据")
    else:
        print("   - 无数据同步结果")
    
    print("\n✅ [信号计算]")
    if signal_results:
        for code, stats in signal_results.items():
            total = stats['total_rows']
            buy_pct = stats['buy_signals'] / total * 100 if total > 0 else 0
            sell_pct = stats['sell_signals'] / total * 100 if total > 0 else 0
            hold_pct = stats['hold_signals'] / total * 100 if total > 0 else 0
            print(f"   - {code}:")
            print(f"     BUY: {stats['buy_signals']} ({buy_pct:.1f}%)")
            print(f"     SELL: {stats['sell_signals']} ({sell_pct:.1f}%)")
            print(f"     HOLD: {stats['hold_signals']} ({hold_pct:.1f}%)")
    else:
        print("   - 无信号计算结果")
    
    print("\n✅ [融合信号]")
    if fusion_results:
        total_return = 0.0
        count = 0
        for code, stats in fusion_results.items():
            print(f"   - {code}:")
            print(f"     BUY: {stats['buy_signals']}, SELL: {stats['sell_signals']}, HOLD: {stats['hold_signals']}")
            print(f"     总收益: {stats['total_return']:.2f}%")
            print(f"     夏普比率: {stats['sharpe_ratio']:.4f}")
            total_return += stats['total_return']
            count += 1
        
        if count > 0:
            avg_return = total_return / count
            print(f"\n   📊 组合平均收益: {avg_return:.2f}%")
    else:
        print("   - 无融合信号结果")
    
    print("\n" + "="*60)
    print("✅ 信号生成完成!")
    print("="*60)

def main():
    """主函数"""
    # 解析参数
    parser = argparse.ArgumentParser(description='股市分析系统 - 信号生成')
    parser.add_argument('--tushare-token', required=True, help='Tushare Pro API Token')
    parser.add_argument('--data-only', action='store_true', help='仅执行数据同步')
    parser.add_argument('--signal-only', action='store_true', help='仅执行信号计算')
    parser.add_argument('--indices', default=','.join(DEFAULT_INDICES), help='指数代码 (逗号分隔)')
    parser.add_argument('--start-date', default='20230101', help='数据起始日期')
    
    args = parser.parse_args()
    
    # 解析指数列表
    indices = [idx.strip() for idx in args.indices.split(',')]
    
    print("="*60)
    print("📈 股市分析系统 - 信号生成")
    print("="*60)
    print(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 指数列表: {', '.join(indices)}")
    print(f"📅 起始日期: {args.start_date}")
    
    data_results = {}
    signal_results = {}
    fusion_results = {}
    
    try:
        # 1. 数据同步
        logger.info("[开始] 数据同步")
        if not args.signal_only:
            data_results = sync_data(indices, args.start_date, args.tushare_token)
        
        # 2. 信号计算
        logger.info("[开始] 信号计算")
        if not args.data_only:
            signal_results = calculate_signals(indices, args.start_date, args.tushare_token)
        
        # 3. 完整报告
        if not args.data_only and not args.signal_only:
            logger.info("[开始] 完整报告")
            fusion_results = generate_full_report(indices, args.start_date, args.tushare_token)
        
        # 4. 打印报告
        print_report(data_results, signal_results, fusion_results)
        
        logger.info("[完成] 信号生成完成")
        
    except Exception as e:
        logger.error(f"[错误] {str(e)}")
        print(f"\n❌ 错误: {str(e)}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
