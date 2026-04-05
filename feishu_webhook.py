#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书机器人Webhook消息发送

使用说明:
1. 在飞书群聊中添加自定义机器人
2. 复制机器人提供的Webhook地址
3. 配置到daily_scheduler.py的FEISHU_WEBHOOK_URL变量

注意: Webhook方式不需要Access Token，直接通过URL验证
"""

import sys
import os
import json
import time
import requests

# 飞书机器人Webhook配置
# 请在飞书群聊中添加自定义机器人后填写
# 示例: https://open.feishu.cn/open-apis/bot/v2/hook/xxx-xxx-xxx
FEISHU_WEBHOOK_URL = ""

def send_feishu_webhook(webhook_url=None, message=""):
    """使用Webhook发送消息"""
    if not webhook_url:
        webhook_url = FEISHU_WEBHOOK_URL
    
    if not webhook_url:
        print("[ERROR] Webhook URL未配置")
        return False
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "msg_type": "text",
        "content": {"text": message}
    }
    
    try:
        response = requests.post(webhook_url, headers=headers, json=payload, timeout=10)
        result = response.json()
        
        if result.get("code") == 0:
            print("[OK] 消息发送成功")
            return True
        else:
            print(f"[ERROR] 消息发送失败: {result.get('msg', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"[ERROR] 消息发送异常: {e}")
        return False


def test_feishu_webhook():
    """测试飞书Webhook连接"""
    print("=" * 60)
    print("[OK] 测试飞书Webhook连接...")
    print("=" * 60)
    
    test_content = (
        f"飞书Webhook测试\n\n"
        f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"Webhook URL: {FEISHU_WEBHOOK_URL[:50]}...\n\n"
        f"配置完成！可以开始推送A股日报了。"
    )
    
    success = send_feishu_webhook(message=test_content)
    
    print("=" * 60)
    if success:
        print("[OK] 飞书Webhook测试完成！")
        print("[OK] 请查看您的飞书群聊消息以确认测试成功")
    else:
        print("[ERROR] 飞书Webhook测试失败")
        print("[INFO] 请检查:")
        print("  1. Webhook URL是否正确")
        print("  2. 机器人是否有发送消息的权限")
        print("  3. 网络连接是否正常")
    print("=" * 60)
    
    return success


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='飞书Webhook测试')
    parser.add_argument('--url', help='Webhook URL')
    parser.add_argument('--send-report', help='发送日报内容')
    
    args = parser.parse_args()
    
    webhook_url = args.url if args.url else None
    
    if args.send_report:
        # 发送日报
        success = send_feishu_webhook(webhook_url, args.send_report)
    else:
        # 测试连接
        success = test_feishu_webhook()
    
    sys.exit(0 if success else 1)
