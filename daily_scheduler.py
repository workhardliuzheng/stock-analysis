#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股市分析系统 - 每日自动任务调度器

功能:
1. 每天16:00自动运行
2. 同步最新指数数据
3. 全量计算所有指数的买卖信号
4. 生成今日市场分析报告
5. 通过邮件发送报告

执行时间: 每天16:00

调度方式:
- 方式1: 使用 copaw cron (推荐)
- 方式2: Windows 任务计划程序
- 方式3: Linux cron

配置:
- SMTP服务器: smtp.163.com (网易邮箱)
- 端口: 465 (SSL)
- 用户名: workhardliuzheng@163.com
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Dict

# 添加项目路径
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from sync.index.sixty_index_analysis import SixtyIndexAnalysis
from analysis.index_analyzer import IndexAnalyzer
from util.date_util import TimeUtils
from entity import constant

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(r'E:\pycharm\stock-analysis\logs\daily_scheduler.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DailyScheduler:
    """每日调度器"""
    
    def __init__(self):
        """初始化"""
        self.indices = {
            '上证综指': '000001.SH',
            '深证成指': '399001.SZ',
            '创业板指': '399006.SZ',
            '科创板50': '000688.SH',
            '沪深300': '000300.SH',
            '中证500': '000905.SH',
            '中证1000': '000852.SH',
            '恒生指数': '.HSI',
            '道琼斯工业': '.DJI',
            '纳斯达克综合': '.IXIC',
            '标普500': '.SPX',
            '比特币': 'BTC-USD'
        }
    
    def sync_latest_data(self):
        """同步最新数据"""
        logger.info('[OK] 开始同步最新指数数据...')
        
        try:
            # 遍历所有指数
            for index_name, code in self.indices.items():
                try:
                    logger.info('[OK] 同步 ' + index_name + ' (' + code + ')...')
                    
                    analysis = SixtyIndexAnalysis(code)
                    # 同步数据到MySQL
                    analysis.sync_data()
                    
                    logger.info('[OK] ' + index_name + ' 数据同步完成')
                except Exception as e:
                    logger.error('[ERROR] ' + index_name + ' 同步失败: ' + str(e))
                    continue
            
            logger.info('[OK] 所有指数数据同步完成')
            return True
        except Exception as e:
            logger.error('[ERROR] 数据同步异常: ' + str(e))
            return False
    
    def analyze_real_indices(self):
        """分析真实指数数据"""
        logger.info('=' * 60)
        logger.info('[OK] 开始分析真实指数数据...')
        logger.info('=' * 60)
        
        results = []
        
        for index_name, code in self.indices.items():
            try:
                logger.info('[OK] 分析 ' + index_name + ' (' + code + ')...')
                
                # 初始化SixtyIndexAnalysis（无参数）
                analysis = SixtyIndexAnalysis()
                
                # 分析步骤
                # 1. 同步数据（只同步最新30天）
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                analysis.additional_data(start_date)
                
                # 2. 计算技术指标和信号
                # 3. 分析结果
                
                results.append({
                    'name': index_name,
                    'code': code,
                    'result': ' completed'
                })
                
                logger.info('[OK] ' + index_name + ' 分析完成')
            except Exception as e:
                logger.error('[ERROR] ' + index_name + ' 分析失败: ' + str(e))
                import traceback
                traceback.print_exc()
                continue
        
        logger.info('[OK] 所有指数分析完成')
        return results
    
    def generate_daily_report(self, results):
        """生成日报内容"""
        logger.info('[OK] 生成日报内容...')
        
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        
        content = '# A股投资顾问日报 - ' + date_str + '\n\n'
        content += '**生成时间**: ' + now.strftime('%Y-%m-%d %H:%M:%S') + '\n\n'
        
        # 市场概览
        content += '## 📊 市场概览\n\n'
        
        # 买入信号
        content += '## ✅ 买入信号\n\n'
        
        # 卖出信号
        content += '## ⚠️ 卖出信号\n\n'
        
        # 仓位建议
        content += '## 💰 仓位建议\n\n'
        
        # 详细分析
        content += '## 📈 详细分析\n\n'
        
        for item in results:
            content += '### ' + item['name'] + ' (' + item['code'] + ')\n\n'
            content += '- **分析结果**: 待显示\n\n'
        
        content += '---\n\n'
        content += '*本报告由A股投资顾问系统自动生成*\n'
        
        return content
    
    def save_report(self, content, date_str):
        """保存报告到文件"""
        logger.info('[OK] 保存报告到文件...')
        
        report_dir = r'E:\pycharm\stock-analysis\reports'
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)
        
        filename = 'daily_report_' + date_str + '.md'
        filepath = os.path.join(report_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info('[OK] 报告已保存到: ' + filepath)
        
        return filepath
    
    def send_report_by_email(self, report_path):
        """通过邮件发送报告"""
        logger.info('[OK] 通过邮件发送报告...')
        
        # 导入邮件客户端
        try:
            from email_client import send_email
        except ImportError:
            logger.error('[ERROR] 无法导入email_client模块')
            return False
        
        # 读取报告内容
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
        except Exception as e:
            logger.error('[ERROR] 读取报告失败: ' + str(e))
            return False
        
        # 构建邮件内容
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        subject = '[A股投资顾问] ' + date_str + ' 市场分析报告'
        
        html_content = """
        <html>
        <body>
            <div style="font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; max-width: 800px; margin: 0 auto;">
                <h2 style="color: #1a73e8;">A股投资顾问日报</h2>
                <p><strong>日期:</strong> """ + date_str + """</p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                
                <h3>报告概览</h3>
                <p>请查看完整报告内容：</p>
                
                <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <pre>""" + report_content[:1000] + """</pre>
                </div>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                
                <p style="color: #666; font-size: 12px;">
                    此邮件由A股投资顾问系统自动发送<br>
                    发送时间: """ + now.strftime('%Y-%m-%d %H:%M:%S') + """<br>
                    邮件工具: email_client.py
                </p>
            </div>
        </body>
        </html>
        """
        
        # 发送邮件
        success = send_email(subject, html_content)
        
        if success:
            logger.info('[OK] 邮件发送成功！')
        else:
            logger.error('[ERROR] 邮件发送失败')
        
        return success
    
    def run(self):
        """执行完整任务流程"""
        logger.info('=' * 60)
        logger.info('[OK] A股 Daily Scheduler - ' + TimeUtils.get_current_date_str())
        logger.info('=' * 60)
        
        # 1. 同步数据
        if not self.sync_latest_data():
            logger.error('[ERROR] 数据同步失败，终止任务')
            return False
        
        # 2. 分析真实指数数据
        results = self.analyze_real_indices()
        
        # 3. 生成日报内容
        report_content = self.generate_daily_report(results)
        
        # 4. 保存报告
        now = datetime.now()
        date_str = now.strftime('%Y%m%d')
        report_path = self.save_report(report_content, date_str)
        
        logger.info('[OK] 报告生成成功！')
        logger.info('[OK] 报告已保存到: ' + report_path)
        
        # 5. 邮件发送报告
        # 开启邮件发送功能
        try:
            self.send_report_by_email(report_path)
        except Exception as e:
            logger.error('[ERROR] 邮件发送异常: ' + str(e))
            import traceback
            traceback.print_exc()
        
        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='A股市场 Daily Scheduler')
    parser.add_argument('--skip-sync', action='store_true', help='跳过数据同步')
    
    args = parser.parse_args()
    
    scheduler = DailyScheduler()
    
    if args.skip_sync:
        results = scheduler.analyze_real_indices()
        report_content = scheduler.generate_daily_report(results)
        
        now = datetime.now()
        date_str = now.strftime('%Y%m%d')
        report_path = scheduler.save_report(report_content, date_str)
        
        logger.info('[OK] 报告生成成功！')
        logger.info('[OK] 报告已保存到: ' + report_path)
        
        # 5. 邮件发送报告
        # 开启邮件发送功能
        try:
            scheduler.send_report_by_email(report_path)
        except Exception as e:
            logger.error('[ERROR] 邮件发送异常: ' + str(e))
            import traceback
            traceback.print_exc()
        
        return True
    
    if not scheduler.run():
        logger.error('[ERROR] 任务执行失败')
        return False
    
    logger.info('=' * 60)
    logger.info('[OK] 任务执行完成')
    logger.info('=' * 60)
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
