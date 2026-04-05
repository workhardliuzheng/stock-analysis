#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
邮件通知工具 - 免费、稳定、无需机器人权限

支持:
- Gmail, QQ邮箱, 163邮箱, 网易企业邮等
- SSL/TLS加密连接
- HTML格式邮件
- 附件支持

配置:
- 修改 FEISHU_EMAIL_RECIPIENT 为您接收通知的邮箱
- 修改 SMTP 配置为您邮箱的SMTP服务器

免费方案，无需飞书机器人权限，10分钟即可配置完成！
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import sys
import os

# 邮件配置 - 请修改为您自己的配置
SMTP_SERVER = "smtp.gmail.com"  # Gmail SMTP服务器
SMTP_PORT = 587                 # TLS端口
SMTP_USER = ""                  # 您的邮箱地址
SMTP_PASSWORD = ""              # 您的邮箱密码或授权码

# 接收通知的邮箱（可以是飞书邮箱，也可以是任何邮箱）
FEISHU_EMAIL_RECIPIENT = ""


def send_email(subject, content, recipients=None):
    """
    发送邮件通知
    
    参数:
        subject: 邮件标题
        content: 邮件内容（支持HTML格式）
        recipients: 收件人列表（默认使用FEISHU_EMAIL_RECIPIENT）
    
    返回:
        bool: 发送成功/失败
    """
    # 使用配置的收件人或传入的收件人
    if recipients is None:
        recipients = [FEISHU_EMAIL_RECIPIENT]
    
    # 检查配置
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[ERROR] 邮件SMTP配置不完整")
        print(f"  SMTP_USER: {SMTP_USER or '未配置'}")
        print(f"  SMTP_PASSWORD: {'*' * len(SMTP_PASSWORD) if SMTP_PASSWORD else '未配置'}")
        return False
    
    if not recipients or not recipients[0]:
        print("[ERROR] 收件人邮箱未配置")
        return False
    
    # 创建邮件
    message = MIMEMultipart('alternative')
    message['Subject'] = Header(subject, 'utf-8')
    message['From'] = SMTP_USER
    message['To'] = ','.join(recipients)
    
    # 添加HTML内容
    html_content = f"""
    <html>
    <body>
        <div style="font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; max-width: 800px; margin: 0 auto;">
            <h2 style="color: #1a73e8;">📊 A股投资顾问通知</h2>
            
            <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                {content}
            </div>
            
            <hr style="border: none; border-top: 1px solid #ddd;">
            
            <p style="color: #666; font-size: 12px; text-align: center;">
                <br>
                🔔 本邮件由A股投资顾问系统自动发送<br>
                ⏰ 发送时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                📧 邮件工具: email_client.py
            </p>
        </div>
    </body>
    </html>
    """
    
    part = MIMEText(html_content, 'html', 'utf-8')
    message.attach(part)
    
    # 发送邮件
    try:
        print(f"[OK] 正在连接SMTP服务器: {SMTP_SERVER}:{SMTP_PORT}")
        
        # 创建SMTP连接（使用STARTTLS）
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls(context=ssl.create_default_context())
        server.login(SMTP_USER, SMTP_PASSWORD)
        
        # 发送邮件
        server.sendmail(SMTP_USER, recipients, message.as_string())
        server.quit()
        
        print(f"[OK] 邮件发送成功！")
        print(f"  发件人: {SMTP_USER}")
        print(f"  收件人: {', '.join(recipients)}")
        print(f"  主题: {subject}")
        
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("[ERROR] SMTP认证失败")
        print("  请检查:")
        print("  1. 邮箱密码/授权码是否正确")
        print("  2. 是否启用了SMTP服务")
        print("  3. Gmail用户需要开启'允许不够安全的应用'或使用应用专用密码")
        return False
        
    except smtplib.SMTPConnectorError as e:
        print(f"[ERROR] SMTP连接失败: {e}")
        print("  请检查:")
        print("  1. SMTP服务器地址和端口是否正确")
        print("  2. 网络连接是否正常")
        return False
        
    except Exception as e:
        print(f"[ERROR] 邮件发送异常: {e}")
        return False


def test_email():
    """测试邮件发送"""
    print("=" * 60)
    print("[OK] 测试邮件发送...")
    print("=" * 60)
    
    # 检查配置
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[ERROR] 邮件SMTP配置不完整")
        print("  请编辑 email_client.py 文件，配置以下变量:")
        print("    SMTP_USER = 'your_email@gmail.com'")
        print("    SMTP_PASSWORD = 'your_password_or_app_password'")
        print("    FEISHU_EMAIL_RECIPIENT = 'your_email@gmail.com'")
        return False
    
    if not FEISHU_EMAIL_RECIPIENT:
        print("[ERROR] 收件人邮箱未配置")
        print("  请编辑 email_client.py 文件，配置以下变量:")
        print("    FEISHU_EMAIL_RECIPIENT = 'your_email@gmail.com'")
        return False
    
    # 测试内容
    subject = "📧 测试邮件 - A股投资顾问系统"
    content = f"""
    <h3>📧 测试邮件</h3>
    <p>这是一封测试邮件，用于验证邮件通知功能是否正常。</p>
    
    <h4>配置信息</h4>
    <ul>
        <li><strong>SMTP服务器:</strong> {SMTP_SERVER}</li>
        <li><strong>SMTP端口:</strong> {SMTP_PORT}</li>
        <li><strong>发件人:</strong> {SMTP_USER}</li>
        <li><strong>收件人:</strong> {FEISHU_EMAIL_RECIPIENT}</li>
    </ul>
    
    <h4>功能说明</h4>
    <p>此邮件由A股投资顾问系统自动发送，用于:</p>
    <ul>
        <li>每日A股信号通知</li>
        <li>重要异常提醒</li>
        <li>系统运行状态</li>
    </ul>
    
    <h3>✅ 配置成功！</h3>
    <p>您的邮件通知功能已准备就绪！</p>
    
    <hr>
    <p style="color: #666; font-size: 12px;">
        ℹ️ 这是系统自动发送的测试邮件，请勿回复。
    </p>
    """
    
    success = send_email(subject, content)
    
    print("=" * 60)
    if success:
        print("[OK] 邮件发送测试完成！")
        print("[OK] 请检查邮箱收件箱（可能在垃圾邮件文件夹）")
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
