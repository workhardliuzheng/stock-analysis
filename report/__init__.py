"""
report 包 - 统一报告生成与邮件发送

模块:
- report_generator: 统一报告生成器 (HTML + 文本)
- html_templates: HTML 报告模板
- email_sender: 邮件发送器 (从 config.yaml 读取配置)
"""

from report.report_generator import UnifiedReportGenerator, ReportResult
from report.email_sender import EmailSender

__all__ = ['UnifiedReportGenerator', 'ReportResult', 'EmailSender']
