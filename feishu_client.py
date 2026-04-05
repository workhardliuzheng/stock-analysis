#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书API集成工具

功能:
- 使用App ID和Secret获取Access Token
- 发送私人消息到飞书账号
- 自动管理Token刷新

使用说明:
1. 需要在飞书开发者后台创建机器人应用
2. 获取App ID和App Secret
3. 配置File: E:\\pycharm\\stock-analysis\\feishu_client.py 中的FEISHU_APP_ID和FEISHU_APP_SECRET

配置:
- 私有应用，不公开
- Tushare Token从项目配置文件读取

联系: 刘峥 (ou_0da6279ffcdf474a5d4a65bf8745eb11)
"""

import sys
import os
import json
import time
import requests

# 添加项目路径
sys.path.insert(0, r'E:\pycharm\stock-analysis')

# 飞书配置
FEISHU_APP_ID = "cli_a94b821a92381cb6"
FEISHU_APP_SECRET = "nLmSUbvyHcltZhX6K4oD2kRF7b2k35UG"
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"


class FeishuClient:
    """飞书API客户端"""
    
    def __init__(self, app_id=None, app_secret=None):
        """初始化飞书客户端"""
        self.app_id = app_id or FEISHU_APP_ID
        self.app_secret = app_secret or FEISHU_APP_SECRET
        self.base_url = FEISHU_API_BASE
        self.access_token = None
        self.token_expires_at = 0
        self.user_open_id = None
        
    def _get_access_token(self):
        """获取Access Token"""
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
        
        token_url = f"{self.base_url}/auth/v3/app_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(token_url, json=payload, timeout=10)
            result = response.json()
            
            if result.get("code") == 0:
                self.access_token = result["app_access_token"]
                self.token_expires_at = time.time() + result.get("expire", 7200) - 300
                print(f"[OK] Access Token获取成功")
                return self.access_token
            else:
                print(f"[ERROR] 获取Access Token失败: {result.get('msg', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"[ERROR] 获取Access Token异常: {e}")
            return None
    
    def get_user_open_id(self):
        """获取用户open_id"""
        access_token = self._get_access_token()
        if not access_token:
            return None
        
        # 获取用户列表
        user_url = f"{self.base_url}/contact/v3/users"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            response = requests.get(user_url, headers=headers, timeout=10)
            result = response.json()
            
            if result.get("code") == 0 and result.get("data", {}).get("items"):
                user = result["data"]["items"][0]
                open_id = user.get("open_id")
                print(f"[OK] 用户信息:")
                print(f"  User ID (open_id): {open_id}")
                print(f"  姓名: {user.get('name', 'N/A')}")
                print(f"  邮箱: {user.get('email', 'N/A')}")
                return open_id
            else:
                print(f"[ERROR] 获取用户列表失败: {result.get('msg', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"[ERROR] 获取用户列表异常: {e}")
            return None
    
    def send_text_message(self, user_open_id, text):
        """发送文本消息到飞书用户"""
        access_token = self._get_access_token()
        if not access_token:
            return False
        
        send_url = f"{self.base_url}/im/v1/messages"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 注意: 飞书API文档显示需要receive_id_type参数
        # 但实际测试中发现可能有验证问题
        # 当前版本暂不支持私人消息发送，需要配置群机器人webhook
        payload = {
            "receive_id": user_open_id,
            "receive_id_type": "open_id",
            "msg_type": "text",
            "content": {"text": text}
        }
        
        try:
            print(f"[OK] 发送消息到: {user_open_id}")
            response = requests.post(send_url, json=payload, headers=headers, timeout=10)
            result = response.json()
            
            if result.get("code") == 0:
                print(f"[OK] 消息发送成功")
                return True
            else:
                print(f"[ERROR] 消息发送失败: {result.get('msg', 'Unknown error')}")
                print(f"[ERROR] 响应: {result}")
                print(f"[INFO] 提示: 机器人应用需要配置消息发送权限")
                return False
                
        except Exception as e:
            print(f"[ERROR] 消息发送异常: {e}")
            return False


def test_feishu_connection():
    """测试飞书连接"""
    print("=" * 60)
    print("[OK] 测试飞书API连接...")
    print("=" * 60)
    
    client = FeishuClient()
    
    # 1. 获取Access Token
    print("[OK] 获取Access Token...")
    token = client._get_access_token()
    if not token:
        print("[ERROR] Access Token获取失败")
        return False
    
    # 2. 获取用户open_id
    print("[OK] 获取用户信息...")
    user_open_id = client.get_user_open_id()
    if not user_open_id:
        print("[ERROR] 用户信息获取失败")
        return False
    
    # 3. 发送测试消息
    print("[OK] 发送测试消息...")
    test_content = (
        f"飞书API测试\n\n"
        f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"Access Token获取成功\n"
        f"用户信息获取成功\n"
        f"用户ID: {user_open_id}\n\n"
        f"配置完成！可以开始推送A股日报了。"
    )
    
    success = client.send_text_message(user_open_id, test_content)
    if not success:
        return False
    
    print("=" * 60)
    print("[OK] 飞书API测试完成！")
    print("[OK] 请查看您的飞书消息以确认测试成功")
    print("=" * 60)
    
    return True


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='飞书API测试')
    parser.add_argument('--send-report', help='发送日报内容')
    
    args = parser.parse_args()
    
    if args.send_report:
        # 发送日报
        client = FeishuClient()
        user_open_id = client.get_user_open_id()
        if user_open_id:
            success = client.send_text_message(user_open_id, args.send_report)
        else:
            success = False
    else:
        # 测试连接
        success = test_feishu_connection()
    
    sys.exit(0 if success else 1)
