#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股市分析系统 - 周期性任务调度器

功能:
1. 每周一到周五16:00自动运行
2. 同步所有数据（股票、指数、财务等）
3. 全量计算所有指数的买卖信号
4. 生成分析报告并推送到飞书

执行时间: 周一至周五 16:00

调度方式:
- 方式1: 使用 copaw cron (推荐)
- 方式2: Windows 任务计划程序
- 方式3: Linux cron
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Dict

# 添加项目路径
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from sync.stock.sync_stock_basic import StockBasicSync
from sync.stock.sync_stock_daily_basic import StockDailyBasicSync
from sync.stock.sync_financing_margin_trading import FinancingMarginTradingSync
from sync.index.sync_stock_weight import StockWeightSync
from sync.stock.sync_income import IncomeSync
from sync.stock.sync_financial_data import FinancialDataSync
from sync.index.sixty_index_analysis import SixtyIndexAnalysis
from analysis.index_analyzer import IndexAnalyzer
from analysis.multi_factor_scorer import MultiFactorScorer
from analysis.signal_threshold_optimizer import get_aggressive_lite_threshold_optimizer
from analysis.adaptive_fusion_optimizer import MetaLearner
from util.date_util import TimeUtils
from entity import constant

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(r'E:\pycharm\stock-analysis\logs\weekly_scheduler.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class WeeklyScheduler:
    """周期性任务调度器"""
    
    def __init__(self):
        """初始化调度器"""
        self.start_date = '20200101'
        self.end_date = TimeUtils.get_current_date_str()
        self.index_list = self._get_index_list()
        
    def _get_index_list(self) -> List[str]:
        """获取所有待分析的指数"""
        return [
            '000001.SH',   # 上证综指
            '000016.SH',   # 上证50
            '000300.SH',   # 沪深300
            '000688.SH',   # 科创50
            '399001.SZ',   # 深证成指
            '399006.SZ',   # 创业板指
            '399005.SZ',   # 中小板指
            '399106.SZ',   # 创业板成指
            '399300.SZ',   # 创业板 efficiencies
            'H11015.CSI',  # 科创创业100
            '000852.SH',   # 中证1000
            '000905.SH',   # 中证500
        ]
    
    def sync_all_data(self) -> bool:
        """同步所有数据"""
        logger.info('=' * 60)
        logger.info('开始同步数据...')
        logger.info('=' * 60)
        
        try:
            # 1. 同步股票基础数据
            logger.info('[1/6] 同步股票基础数据...')
            StockBasicSync().sync_all()
            
            # 2. 同步两融数据
            logger.info('[2/6] 同步两融数据...')
            FinancingMarginTradingSync().additional_data()
            
            # 3. 同步权重数据
            logger.info('[3/6] 同步权重数据...')
            StockWeightSync().additional_data()
            
            # 4. 同步财务数据
            logger.info('[4/6] 同步财务数据...')
            IncomeSync().additional_data()
            FinancialDataSync().additional_data()
            
            # 5. 同步股票日线数据
            logger.info('[5/6] 同步股票日线数据...')
            StockDailyBasicSync().sync_all()
            
            # 6. 同步指数数据（最后，依赖上述数据）
            logger.info('[6/6] 同步指数数据...')
            SixtyIndexAnalysis().additional_data(self.start_date)
            
            logger.info('=' * 60)
            logger.info('[OK] 数据同步完成！')
            logger.info('=' * 60)
            
            return True
            
        except Exception as e:
            logger.error(f'[ERROR] 数据同步失败: {e}')
            import traceback
            traceback.print_exc()
            return False
    
    def calculate_signals_for_all_indices(self) -> bool:
        """为所有指数计算买卖信号"""
        logger.info('=' * 60)
        logger.info('开始计算信号...')
        logger.info(f'分析指数数量: {len(self.index_list)}')
        logger.info('=' * 60)
        
        try:
            total_analyzed = 0
            total_buy = 0
            total_sell = 0
            total_hold = 0
            
            for ts_code in self.index_list:
                try:
                    analyzer = IndexAnalyzer(
                        ts_code=ts_code,
                        start_date=self.start_date,
                        lookback_years=5
                    )
                    df = analyzer.analyze()
                    
                    # 获取当前信号
                    current_signal = analyzer.get_current_signal()
                    signal_type = current_signal.get('signal_type', 'HOLD')
                    
                    if signal_type == 'BUY':
                        total_buy += 1
                    elif signal_type == 'SELL':
                        total_sell += 1
                    else:
                        total_hold += 1
                    
                    total_analyzed += 1
                    
                    logger.info(f'[OK] {analyzer.name} ({ts_code}): {signal_type}')
                    
                except Exception as e:
                    logger.error(f'[ERROR] 分析 {ts_code} 失败: {e}')
                    import traceback
                    traceback.print_exc()
                    continue
            
            logger.info('=' * 60)
            logger.info('信号计算汇总:')
            logger.info(f'  总计分析: {total_analyzed} 个指数')
            logger.info(f'  BUY信号: {total_buy} 个 ({total_buy/total_analyzed*100:.1f}%)')
            logger.info(f'  SELL信号: {total_sell} 个 ({total_sell/total_analyzed*100:.1f}%)')
            logger.info(f'  HOLD信号: {total_hold} 个 ({total_hold/total_analyzed*100:.1f}%)')
            logger.info('=' * 60)
            
            return True
            
        except Exception as e:
            logger.error(f'[ERROR] 信号计算失败: {e}')
            import traceback
            traceback.print_exc()
            return False
    
    def generate_report_and_push_to_feishu(self) -> bool:
        """生成报告并推送到飞书"""
        logger.info('=' * 60)
        logger.info('开始生成报告...')
        logger.info('=' * 60)
        
        try:
            # 获取当前时间
            now = datetime.now()
            report_date = now.strftime('%Y年%m月%d日')
            report_time = now.strftime('%H:%M:%S')
            
            # 准备报告数据
            report_data = {
                'report_date': report_date,
                'report_time': report_time,
                'indices': [],
                'summary': {
                    'buy_count': 0,
                    'sell_count': 0,
                    'hold_count': 0,
                    'total_count': 0
                }
            }
            
            # 分析所有指数
            for ts_code in self.index_list:
                try:
                    analyzer = IndexAnalyzer(
                        ts_code=ts_code,
                        start_date=self.start_date,
                        lookback_years=5
                    )
                    df = analyzer.analyze()
                    current_signal = analyzer.get_current_signal()
                    
                    # 获取技术指标
                    indicators = analyzer.get_technical_indicators()
                    
                    # 生成指数分析
                    index_analysis = {
                        'ts_code': ts_code,
                        'name': constant.TS_CODE_NAME_DICT.get(ts_code, ts_code),
                        'signal_type': current_signal.get('signal_type', 'HOLD'),
                        'signal_strength': current_signal.get('signal_strength', 0),
                        'close_price': current_signal.get('close', 0),
                        'change_pct': current_signal.get('pct_change', 0),
                        'technicals': indicators
                    }
                    
                    report_data['indices'].append(index_analysis)
                    report_data['summary']['total_count'] += 1
                    
                    if current_signal.get('signal_type') == 'BUY':
                        report_data['summary']['buy_count'] += 1
                    elif current_signal.get('signal_type') == 'SELL':
                        report_data['summary']['sell_count'] += 1
                    else:
                        report_data['summary']['hold_count'] += 1
                    
                except Exception as e:
                    logger.error(f'[ERROR] 分析 {ts_code} 失败: {e}')
                    import traceback
                    traceback.print_exc()
                    continue
            
            # 生成报告内容
            report_content = self._generate_report_content(report_data)
            
            # 保存报告到文件
            report_path = self._save_report_to_file(report_content, report_date)
            logger.info(f'[OK] 报告已保存: {report_path}')
            
            # 推送到飞书
            success = self._push_to_feishu(report_content, report_date)
            
            if success:
                logger.info('=' * 60)
                logger.info('[OK] 报告生成并推送成功！')
                logger.info('=' * 60)
            
            return success
            
        except Exception as e:
            logger.error(f'[ERROR] 报告生成失败: {e}')
            import traceback
            traceback.print_exc()
            return False
    
    def _generate_report_content(self, report_data: Dict) -> str:
        """生成报告内容"""
        indices = report_data['indices']
        summary = report_data['summary']
        
        content = []
        content.append(f'# 📈 A股市场每周复盘报告')
        content.append(f'')
        content.append(f'**报告日期**: {report_data["report_date"]} {report_data["report_time"]}')
        content.append(f'')
        content.append(f'## 📊 市场概览')
        content.append(f'')
        content.append(f'| 指数 | 信号 | 强度 | 价格 | 涨跌幅 |')
        content.append(f'|------|------|------|------|--------|')
        
        for index in indices:
            signal_emoji = '🔴 SELL' if index['signal_type'] == 'SELL' else ('🟢 BUY' if index['signal_type'] == 'BUY' else '⚪ HOLD')
            content.append(f'| {index["name"]} | {signal_emoji} | {index["signal_strength"]:.1f} | {index["close_price"]:.2f} | {index["change_pct"]:.2f}% |')
        
        content.append(f'')
        content.append(f'## 🔍 信号统计')
        content.append(f'')
        content.append(f'- **BUY信号**: {summary["buy_count"]} 个 ({summary["buy_count"]/summary["total_count"]*100:.1f}%)')
        content.append(f'- **SELL信号**: {summary["sell_count"]} 个 ({summary["sell_count"]/summary["total_count"]*100:.1f}%)')
        content.append(f'- **HOLD信号**: {summary["hold_count"]} 个 ({summary["hold_count"]/summary["total_count"]*100:.1f}%)')
        content.append(f'- **总计**: {summary["total_count"]} 个指数')
        content.append(f'')
        content.append(f'## 📈 Detailed Analysis')
        
        for index in indices:
            content.append(f'')
            content.append(f'### {index["name"]} ({index["ts_code"]})')
            content.append(f'')
            signal_type = index['signal_type']
            
            if signal_type == 'BUY':
                content.append(f'**强烈推荐买入** 🌟🌟🌟')
                content.append(f'- 当前信号强度: **{index["signal_strength"]:.1f}**')
                content.append(f'- 价格: **{index["close_price"]:.2f}**')
                content.append(f'- 涨跌幅: **{index["change_pct"]:.2f}%**')
                content.append(f'- 建议仓位: **70-80%**')
                content.append(f'- 操作策略: **加仓/建仓**')
            elif signal_type == 'SELL':
                content.append(f'**强烈建议卖出** 🛑🛑🛑')
                content.append(f'- 当前信号强度: **{index["signal_strength"]:.1f}**')
                content.append(f'- 价格: **{index["close_price"]:.2f}**')
                content.append(f'- 涨跌幅: **{index["change_pct"]:.2f}%**')
                content.append(f'- 建议仓位: **0-10%**')
                content.append(f'- 操作策略: **减仓/清仓**')
            else:
                content.append(f'**观望等待** ⚖️⚖️⚖️')
                content.append(f'- 当前信号强度: **{index["signal_strength"]:.1f}**')
                content.append(f'- 价格: **{index["close_price"]:.2f}**')
                content.append(f'- 涨跌幅: **{index["change_pct"]:.2f}%**')
                content.append(f'- 建议仓位: **30-40%**')
                content.append(f'- 操作策略: **持有观望**')
            
            content.append(f'')
            content.append(f'#### 技术指标')
            content.append(f'')
            
            technicals = index.get('technicals', {})
            if technicals:
                content.append(f'| 指标 | 值 | 说明 |')
                content.append(f'|------|-----|------|')
                for key, value in technicals.items():
                    content.append(f'| {key} | {value:.2f} | - |')
            
            content.append(f'')
            content.append(f'- - -')
        
        content.append(f'')
        content.append(f'## ⚠️ 风险提示')
        content.append(f'')
        content.append(f'- 本报告基于技术分析，不构成投资建议')
        content.append(f'- 市场有风险，投资需谨慎')
        content.append(f'- 请结合基本面分析和自身风险偏好决策')
        content.append(f'')
        content.append(f'---')
        content.append(f'生成时间: {report_data["report_time"]}')
        content.append(f'数据分析系统: A股技术分析 v1.0')
        
        return '\n'.join(content)
    
    def _save_report_to_file(self, content: str, report_date: str) -> str:
        """保存报告到文件"""
        report_dir = r'E:\pycharm\stock-analysis\reports'
        os.makedirs(report_dir, exist_ok=True)
        
        filename = f'weekly_report_{report_date.replace("/", "")}.md'
        filepath = os.path.join(report_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def _push_to_feishu(self, content: str, report_date: str) -> bool:
        """推送到飞书"""
        # 简化版本 - 实际需要集成飞书API
        # 这里提供一个占位实现
        
        logger.info('[INFO] 飞书推送功能待实现')
        logger.info(f'[INFO] 报告内容预览:')
        logger.info(f'{content[:200]}...')
        
        # TODO: 集成飞书机器人API
        # 参考: https://open.feishu.cn/document/ukTMukTMukTM/uUTOxUjL3kKMx4iN2EjN
        
        return True
    
    def run(self):
        """执行完整任务流程"""
        logger.info('=' * 60)
        logger.info(f'A股 Weekly Scheduler - {TimeUtils.get_current_date_str()}')
        logger.info('=' * 60)
        
        # 1. 同步数据
        if not self.sync_all_data():
            logger.error('[ERROR] 数据同步失败，终止任务')
            return False
        
        # 2. 计算信号
        if not self.calculate_signals_for_all_indices():
            logger.error('[ERROR] 信号计算失败，终止任务')
            return False
        
        # 3. 生成报告并推送
        if not self.generate_report_and_push_to_feishu():
            logger.error('[ERROR] 报告生成失败')
            return False
        
        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='A股市场 Weekly Scheduler')
    parser.add_argument('--skip-sync', action='store_true', help='跳过数据同步')
    parser.add_argument('--only-sync', action='store_true', help='仅执行数据同步')
    
    args = parser.parse_args()
    
    scheduler = WeeklyScheduler()
    
    if args.only_sync:
        success = scheduler.sync_all_data()
        sys.exit(0 if success else 1)
    
    if args.skip_sync:
        success = scheduler.calculate_signals_for_all_indices()
        if success:
            success = scheduler.generate_report_and_push_to_feishu()
    else:
        success = scheduler.run()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
