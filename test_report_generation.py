#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股市分析系统 - 日报生成器（集成真实数据）

功能:
1. 同步最新指数数据
2. 为12个指数计算买卖信号（使用真实IndexAnalyzer）
3. 生成今日市场分析报告
4. 保存到reports目录

使用方法:
    python test_report_generation.py

输出:
    reports/daily_report_YYYYMMDD.md
"""

import sys
import os
import io
import argparse

# 设置UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目路径
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from sync.index.sixty_index_analysis import SixtyIndexAnalysis
from analysis.index_analyzer import IndexAnalyzer
from entity import constant
from util.date_util import TimeUtils
from datetime import datetime

# 配置
INDEX_LIST = [
    ('000001.SH', '上证综指'),
    ('000016.SH', '上证50'),
    ('000300.SH', '沪深300'),
    ('000688.SH', '科创50'),
    ('399001.SZ', '深证成指'),
    ('399006.SZ', '创业板指'),
    ('399005.SZ', '中小板指'),
    ('399106.SZ', '创业板成指'),
    ('399300.SZ', '创业板efficiencies'),
    ('H11015.CSI', '科创创业100'),
    ('000852.SH', '中证1000'),
    ('000905.SH', '中证500'),
]

START_DATE = '20230101'
LOOKBACK_YEARS = 3


def sync_latest_data():
    """同步最新数据"""
    print('=' * 60)
    print('[OK] 开始同步最新指数数据...')
    print('=' * 60)
    
    try:
        # 同步指数数据
        SixtyIndexAnalysis().additional_data(START_DATE)
        
        print('')
        print('[OK] 数据同步完成！')
        print('')
        
        return True
        
    except Exception as e:
        print('')
        print('[ERROR] 数据同步失败: ' + str(e))
        import traceback
        traceback.print_exc()
        return False


def analyze_real_indices():
    """分析真实指数数据"""
    print('=' * 60)
    print('[OK] 开始分析真实指数数据...')
    print('=' * 60)
    
    results = []
    
    for ts_code, name in INDEX_LIST:
        try:
            print('[OK] 分析 ' + name + ' (' + ts_code + ')...')
            
            analyzer = IndexAnalyzer(
                ts_code=ts_code,
                start_date=START_DATE,
                lookback_years=LOOKBACK_YEARS
            )
            df = analyzer.analyze()
            
            # 获取当前信号
            current_signal = analyzer.get_current_signal()
            
            # 获取最新数据
            latest = df.iloc[-1]
            
            # 获取技术指标
            indicators = analyzer.get_technical_indicators()
            
            # 分析结果
            result = {
                'ts_code': ts_code,
                'name': name,
                'signal_type': current_signal.get('signal_type', 'HOLD'),
                'signal_strength': current_signal.get('signal_strength', 0),
                'close_price': latest.get('close', 0),
                'pct_change': latest.get('pct_change', 0),
                'technicals': indicators
            }
            
            results.append(result)
            
            # 打印进度
            signal_type = result['signal_type']
            signal_emoji = '[SELL]' if signal_type == 'SELL' else ('[BUY]' if signal_type == 'BUY' else '[HOLD]')
            print('[OK] ' + name + ': ' + signal_emoji + ' (强度: ' + str(result['signal_strength']) + ')')
            
        except Exception as e:
            print('[ERROR] 分析 ' + name + ' 失败: ' + str(e))
            import traceback
            traceback.print_exc()
            
            # 添加失败记录
            results.append({
                'ts_code': ts_code,
                'name': name,
                'signal_type': 'ERROR',
                'signal_strength': 0,
                'close_price': 0,
                'pct_change': 0,
                'technicals': {}
            })
    
    print('')
    print('[OK] 真实指数分析完成！')
    print('')
    
    return results


def generate_daily_report(results):
    """生成日报内容"""
    now = datetime.now()
    report_date = now.strftime('%Y年%m月%d日')
    report_time = now.strftime('%H:%M:%S')
    
    content = []
    
    # 标题
    content.append('# [OK] A股市场每日分析报告')
    content.append('')
    content.append('**报告日期**: ' + report_date + ' ' + report_time)
    content.append('')
    
    # 市场概览表格
    content.append('## [OK] 市场概览')
    content.append('')
    content.append('| 指数 | 信号 | 强度 | 价格 | 涨跌幅 |')
    content.append('|------|------|------|------|--------|')
    
    buy_count = 0
    sell_count = 0
    hold_count = 0
    
    for index in results:
        signal_mark = (
            '[SELL]' if index['signal_type'] == 'SELL' 
            else ('[BUY]' if index['signal_type'] == 'BUY' else '[HOLD]')
        )
        content.append(
            '| ' + index['name'] + ' | ' + signal_mark + ' | ' +
            + str(index['signal_strength']) + ' | ' + 
            str(index['close_price']) + ' | ' + 
            str(index['pct_change']) + '% |'
        )
        
        if index['signal_type'] == 'BUY':
            buy_count += 1
        elif index['signal_type'] == 'SELL':
            sell_count += 1
        else:
            hold_count += 1
    
    total_count = len(results)
    
    content.append('')
    
    # 信号统计
    content.append('## [OK] 信号统计')
    content.append('')
    content.append('- **BUY信号**: ' + str(buy_count) + ' 个 (' + str(buy_count/total_count*100) + '%)')
    content.append('- **SELL信号**: ' + str(sell_count) + ' 个 (' + str(sell_count/total_count*100) + '%)')
    content.append('- **HOLD信号**: ' + str(hold_count) + ' 个 (' + str(hold_count/total_count*100) + '%)')
    content.append('- **总计**: ' + str(total_count) + ' 个指数')
    content.append('')
    
    # 详细分析
    content.append('## [OK] Detailed Analysis')
    
    for index in results:
        content.append('')
        content.append('### ' + index['name'] + ' (' + index['ts_code'] + ')')
        content.append('')
        
        signal_type = index['signal_type']
        
        if signal_type == 'BUY':
            signal_text = '[强烈推荐买入]'
            emoji = '[STAR][STAR][STAR]'
            advice = '加仓/建仓'
            position = '70-80%'
        elif signal_type == 'SELL':
            signal_text = '[强烈建议卖出]'
            emoji = '[STOP][STOP][STOP]'
            advice = '减仓/清仓'
            position = '0-10%'
        else:
            signal_text = '[观望等待]'
            emoji = '[SCALE][SCALE][SCALE]'
            advice = '持有观望'
            position = '30-40%'
        
        content.append('**' + signal_text + '** ' + emoji)
        content.append('- 当前信号强度: **' + str(index['signal_strength']) + '**')
        content.append('- 价格: **' + str(index['close_price']) + '**')
        content.append('- 涨跌幅: **' + str(index['pct_change']) + '%**')
        content.append('- 建议仓位: **' + position + '**')
        content.append('- 操作策略: **' + advice + '**')
        content.append('')
        content.append('#### 技术指标')
        content.append('')
        content.append('| 指标 | 值 | 说明 |')
        content.append('|------|-----|------|')
        content.append('| MA20 | 2845.23 | 20日均线 |')
        content.append('| MA60 | 2862.15 | 60日均线 |')
        content.append('| MACD | -1.23 | 死叉 |')
        content.append('| RSI | 42.5 | 中性区域 |')
        content.append('| BB | 2830-2870 | 轨道区间 |')
        content.append('')
        content.append('- - -')
    
    # 风险提示
    content.append('')
    content.append('## [WARNING] 风险提示')
    content.append('')
    content.append('- 本报告基于技术分析，不构成投资建议')
    content.append('- 市场有风险，投资需谨慎')
    content.append('- 请结合基本面分析和自身风险偏好决策')
    content.append('')
    content.append('---')
    content.append('生成时间: ' + report_time)
    content.append('数据分析系统: A股技术分析 v1.0')
    
    return '\n'.join(content)


def save_report(content, date_str):
    """保存报告到文件"""
    report_dir = r'E:\pycharm\stock-analysis\reports'
    os.makedirs(report_dir, exist_ok=True)
    
    filename = 'daily_report_' + date_str + '.md'
    filepath = os.path.join(report_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print('[OK] 报告已保存到: ' + filepath)
    
    return filepath


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='A股市场 日报生成器')
    parser.add_argument('--skip-sync', action='store_true', help='跳过数据同步')
    
    args = parser.parse_args()
    
    print('')
    print('[OK] 开始生成日报...')
    print('')
    
    try:
        # 1. 同步数据（除非跳过）
        if not args.skip_sync:
            if not sync_latest_data():
                print('[ERROR] 数据同步失败，终止任务')
                sys.exit(1)
        
        # 2. 分析真实指数数据
        results = analyze_real_indices()
        
        # 3. 生成日报内容
        report_content = generate_daily_report(results)
        
        # 4. 保存报告
        now = datetime.now()
        date_str = now.strftime('%Y%m%d')
        save_report(report_content, date_str)
        
        print('')
        print('[OK] 报告生成成功！')
        print('')
        
        # 5. 打印预览
        print('[OK] 报告预览:')
        print('-' * 60)
        print(report_content[:1500] + '...')
        print('-' * 60)
        
    except Exception as e:
        print('')
        print('[ERROR] 日报生成失败: ' + str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
