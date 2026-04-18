"""
统一配置加载器

从 config.yaml 加载配置，提供类型化的访问接口。
支持 database / token / email / report 等配置节。
"""

import os
import yaml

# 项目根目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_CONFIG_PATH = os.path.join(_PROJECT_ROOT, 'config.yaml')

# 缓存
_config_cache = None


def load_config(config_path: str = None) -> dict:
    """
    加载 config.yaml，结果缓存。

    Args:
        config_path: 配置文件路径，默认为项目根目录的 config.yaml

    Returns:
        dict: 完整配置字典
    """
    global _config_cache
    if _config_cache is not None and config_path is None:
        return _config_cache

    path = config_path or _DEFAULT_CONFIG_PATH
    if not os.path.exists(path):
        print(f"[WARNING] 配置文件不存在: {path}")
        return {}

    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f) or {}

    if config_path is None:
        _config_cache = config

    return config


def reload_config() -> dict:
    """强制重新加载配置"""
    global _config_cache
    _config_cache = None
    return load_config()


def get_database_config() -> dict:
    """
    返回数据库配置。

    Returns:
        dict: {'host', 'database', 'user', 'password'}
    """
    config = load_config()
    return config.get('database', {})


def get_tushare_token() -> str:
    """
    返回 Tushare Pro API token。

    Returns:
        str: token 字符串
    """
    config = load_config()
    return config.get('token', '')


def get_email_config() -> dict:
    """
    返回邮件配置，优先从 config.yaml 读取，fallback 到环境变量。

    Returns:
        dict: {
            'smtp_server': str,
            'smtp_port': int,
            'smtp_user': str,
            'smtp_password': str,
            'from_email': str,
            'default_recipients': list[str],
            'subject_prefix': str
        }
    """
    config = load_config()
    email_cfg = config.get('email', {})

    if email_cfg:
        return {
            'smtp_server': email_cfg.get('smtp_server', ''),
            'smtp_port': int(email_cfg.get('smtp_port', 465)),
            'smtp_user': email_cfg.get('smtp_user', ''),
            'smtp_password': email_cfg.get('smtp_password', ''),
            'from_email': email_cfg.get('from_email', email_cfg.get('smtp_user', '')),
            'default_recipients': email_cfg.get('default_recipients', []),
            'subject_prefix': email_cfg.get('subject_prefix', '[A股投资顾问]'),
        }

    # fallback 到环境变量
    smtp_user = os.environ.get('SMTP_USER', '')
    return {
        'smtp_server': os.environ.get('SMTP_HOST', ''),
        'smtp_port': int(os.environ.get('SMTP_PORT', '465')),
        'smtp_user': smtp_user,
        'smtp_password': os.environ.get('SMTP_PASSWORD', ''),
        'from_email': os.environ.get('SMTP_FROM', smtp_user),
        'default_recipients': [],
        'subject_prefix': '[A股投资顾问]',
    }


def get_report_config() -> dict:
    """
    返回报告配置。

    Returns:
        dict: {'output_dir': str}
    """
    config = load_config()
    report_cfg = config.get('report', {})
    return {
        'output_dir': report_cfg.get('output_dir', 'reports'),
    }
