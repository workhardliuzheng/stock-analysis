"""
邮件发送器

从 config.yaml 读取 SMTP 配置，支持 SSL(465) 和 TLS(587)。
"""

import os
import sys
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.header import Header
from email.utils import formatdate
from email import encoders
from typing import List, Optional, Tuple

# 确保项目根目录在 path 中
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


class EmailSender:
    """
    邮件发送器

    优先从 config.yaml 的 email 节读取配置，
    fallback 到环境变量，最后 fallback 到显式传入的配置。
    """

    def __init__(self, smtp_config: dict = None):
        """
        Args:
            smtp_config: 显式 SMTP 配置，格式:
                {
                    'smtp_server': str,
                    'smtp_port': int,
                    'smtp_user': str,
                    'smtp_password': str,
                    'from_email': str,
                    'default_recipients': list[str],
                    'subject_prefix': str,
                }
                如果为 None，从 config.yaml 读取。
        """
        if smtp_config is None:
            smtp_config = self._load_config()
        self.config = smtp_config

    def send(self,
             subject: str,
             html_content: str,
             to_emails: Optional[List[str]] = None,
             attachment_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        发送 HTML 格式邮件。

        Args:
            subject: 邮件主题
            html_content: HTML 正文
            to_emails: 收件人列表，默认使用配置中的 default_recipients
            attachment_path: 可选附件文件路径

        Returns:
            (success, message)
        """
        cfg = self.config

        if not cfg.get('smtp_user') or not cfg.get('smtp_password'):
            return False, "邮件 SMTP 配置不完整 (smtp_user 或 smtp_password 缺失)"

        if to_emails is None:
            to_emails = cfg.get('default_recipients', [])
        if isinstance(to_emails, str):
            to_emails = [e.strip() for e in to_emails.split(',')]

        if not to_emails:
            return False, "收件人为空"

        # 主题前缀
        prefix = cfg.get('subject_prefix', '')
        if prefix and not subject.startswith(prefix):
            full_subject = f"{prefix} {subject}"
        else:
            full_subject = subject

        # 构建邮件
        msg = MIMEMultipart('mixed')
        msg['From'] = cfg.get('from_email', cfg.get('smtp_user', ''))
        msg['To'] = ','.join(to_emails)
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = Header(full_subject, 'utf-8')

        # HTML 正文
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)

        # 附件
        if attachment_path and os.path.exists(attachment_path):
            try:
                with open(attachment_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    filename = os.path.basename(attachment_path)
                    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                    msg.attach(part)
            except Exception as e:
                print(f"[WARNING] 附件添加失败: {e}")

        # 发送
        smtp_server = cfg.get('smtp_server', '')
        smtp_port = int(cfg.get('smtp_port', 465))
        smtp_user = cfg.get('smtp_user', '')
        smtp_password = cfg.get('smtp_password', '')

        try:
            print(f"[OK] 正在连接 SMTP 服务器: {smtp_server}:{smtp_port}")

            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=15)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
                server.starttls(context=ssl.create_default_context())

            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_emails, msg.as_string())
            server.quit()

            print(f"[OK] 邮件发送成功")
            print(f"  发件人: {smtp_user}")
            print(f"  收件人: {', '.join(to_emails)}")
            print(f"  主题: {full_subject}")
            return True, "邮件发送成功"

        except smtplib.SMTPAuthenticationError:
            msg_text = "SMTP 认证失败，请检查邮箱密码/授权码"
            print(f"[ERROR] {msg_text}")
            return False, msg_text

        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected) as e:
            msg_text = f"SMTP 连接失败: {e}"
            print(f"[ERROR] {msg_text}")
            return False, msg_text

        except Exception as e:
            msg_text = f"邮件发送异常: {e}"
            print(f"[ERROR] {msg_text}")
            return False, msg_text

    def test_connection(self) -> Tuple[bool, str]:
        """
        测试 SMTP 连接（不发送邮件）。

        Returns:
            (success, message)
        """
        cfg = self.config
        smtp_server = cfg.get('smtp_server', '')
        smtp_port = int(cfg.get('smtp_port', 465))
        smtp_user = cfg.get('smtp_user', '')
        smtp_password = cfg.get('smtp_password', '')

        if not smtp_user or not smtp_password:
            return False, "SMTP 配置不完整"

        try:
            print(f"[OK] 测试连接 {smtp_server}:{smtp_port}...")
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                server.starttls(context=ssl.create_default_context())

            server.login(smtp_user, smtp_password)
            server.quit()
            print("[OK] SMTP 连接测试成功")
            return True, "连接成功"

        except Exception as e:
            msg_text = f"连接失败: {e}"
            print(f"[ERROR] {msg_text}")
            return False, msg_text

    @staticmethod
    def _load_config() -> dict:
        """从 config.yaml 加载邮件配置。"""
        try:
            from util.config_loader import get_email_config
            return get_email_config()
        except Exception as e:
            print(f"[WARNING] 无法从 config.yaml 加载邮件配置: {e}")
            return {
                'smtp_server': os.environ.get('SMTP_HOST', ''),
                'smtp_port': int(os.environ.get('SMTP_PORT', '465')),
                'smtp_user': os.environ.get('SMTP_USER', ''),
                'smtp_password': os.environ.get('SMTP_PASSWORD', ''),
                'from_email': os.environ.get('SMTP_FROM', ''),
                'default_recipients': [],
                'subject_prefix': '[A股投资顾问]',
            }
