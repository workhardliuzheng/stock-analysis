#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
邮件通知工具

配置统一从 config.yaml 的 email 节读取。
底层使用 report.email_sender.EmailSender 实现。

用法:
    python email_client.py --test           # 测试邮件发送
    python email_client.py --send-report "内容"  # 发送报告
"""

import sys
import os
from datetime import datetime

# 确保项目根目录在 path 中
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from report.email_sender import EmailSender
from util.config_loader import get_email_config


def send_email(subject, content, recipients=None):
    """
    发送邮件通知 (向后兼容接口)

    参数:
        subject: 邮件标题
        content: 邮件内容 (支持 HTML 格式)
        recipients: 收件人列表 (默认使用 config.yaml 中的 default_recipients)

    返回:
        bool: 发送成功/失败
    """
    sender = EmailSender()

    # 包装 HTML 内容
    html_content = f"""
    <html>
    <body>
        <div style="font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; max-width: 800px; margin: 0 auto;">
            <h2 style="color: #1a73e8;">A股投资顾问通知</h2>

            <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                {content}
            </div>

            <hr style="border: none; border-top: 1px solid #ddd;">

            <p style="color: #666; font-size: 12px; text-align: center;">
                <br>
                本邮件由A股投资顾问系统自动发送<br>
                发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            </p>
        </div>
    </body>
    </html>
    """

    success, msg = sender.send(subject, html_content, to_emails=recipients)
    return success


def test_email():
    """测试邮件发送"""
    print("=" * 60)
    print("[OK] 测试邮件发送...")
    print("=" * 60)

    cfg = get_email_config()
    smtp_user = cfg.get('smtp_user', '')
    smtp_server = cfg.get('smtp_server', '')
    smtp_port = cfg.get('smtp_port', 465)
    recipients = cfg.get('default_recipients', [])

    if not smtp_user or not cfg.get('smtp_password'):
        print("[ERROR] 邮件 SMTP 配置不完整")
        print("  请编辑 config.yaml 文件的 email 节:")
        print("    email:")
        print("      smtp_server: smtp.163.com")
        print("      smtp_port: 465")
        print("      smtp_user: your_email@163.com")
        print("      smtp_password: your_auth_code")
        return False

    if not recipients:
        print("[ERROR] 收件人邮箱未配置")
        print("  请在 config.yaml 的 email.default_recipients 中配置")
        return False

    subject = "[测试邮件] A股投资顾问系统"
    content = f"""
    <h3>测试邮件</h3>
    <p>这是一封测试邮件，用于验证邮件通知功能是否正常。</p>

    <h4>配置信息</h4>
    <ul>
        <li><strong>SMTP服务器:</strong> {smtp_server}</li>
        <li><strong>SMTP端口:</strong> {smtp_port}</li>
        <li><strong>发件人:</strong> {smtp_user}</li>
        <li><strong>收件人:</strong> {recipients[0] if recipients else '未配置'}</li>
    </ul>

    <h3>配置成功!</h3>
    <p>您的邮件通知功能已准备就绪!</p>
    """

    success = send_email(subject, content)

    print("=" * 60)
    if success:
        print("[OK] 邮件发送测试完成!")
        print("[OK] 请检查邮箱收件箱 (可能在垃圾邮件文件夹)")
    else:
        print("[ERROR] 邮件发送测试失败")
    print("=" * 60)

    return success


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='邮件通知工具')
    parser.add_argument('--test', action='store_true', help='测试邮件发送')
    parser.add_argument('--send-report', help='发送报告内容')
    parser.add_argument('--subject', default='A股投资顾问通知', help='邮件主题')

    args = parser.parse_args()

    if args.test:
        success = test_email()
    elif args.send_report:
        success = send_email(args.subject, args.send_report)
    else:
        parser.print_help()
        success = False

    sys.exit(0 if success else 1)
