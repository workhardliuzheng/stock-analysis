# 邮件通知配置指南

## 📧 免费邮件通知方案（无需机器人权限）

### 方案概述
- **免费程度**: ✅ 完全免费
- **配置难度**: ⭐⭐⭐ （10分钟搞定）
- **稳定性**: ⭐⭐⭐⭐⭐ （SMTP标准协议）
- **优势**: 
  - 无需飞书机器人权限
  - 直接邮件到邮箱（飞书邮箱/Gmail/QQ邮箱等都行）
  - 支持HTML格式，图文并茂
  - 任何邮箱都能接收

---

## 🚀 快速配置（5分钟）

### 步骤1: 准备发件人邮箱
选择以下任一邮箱（都免费）：

| 邮箱服务商 | SMTP服务器 | 端口 | 开启SMTP方式 |
|-----------|-----------|------|-------------|
| **Gmail** | smtp.gmail.com | 587 | 开启"允许不够安全的应用"或使用应用专用密码 |
| **QQ邮箱** | smtp.qq.com | 587 | 设置→账户→POP3/IMAP/SMTP服务→开启 |
| **163邮箱** | smtp.163.com | 25/465 | 设置→POP3/IMAP/SMTP服务→开启 |
| **网易企业邮** | smtp.mxhichina.com | 465/587 | 管理后台开启SMTP |
| **Outlook/Hotmail** | smtp-mail.outlook.com | 587 | 直接使用 |

### 步骤2: 配置SMTP信息
编辑 `email_client.py` 文件:

```python
# 邮件配置 - 请修改为您自己的配置
SMTP_SERVER = "smtp.gmail.com"  # 替换为您的SMTP服务器
SMTP_PORT = 587                 # TLS端口
SMTP_USER = "your_email@gmail.com"  # 替换为您的邮箱
SMTP_PASSWORD = "your_password_or_app_password"  # 替换为您的密码/授权码

# 接收通知的邮箱（可以是飞书邮箱，也可以是任何邮箱）
FEISHU_EMAIL_RECIPIENT = "your_email@gmail.com"  # 替换为您接收邮件的邮箱
```

### 步骤3: 测试邮件发送
```bash
cd E:\pycharm\stock-analysis
python email_client.py --test
```

---

## 📋 Gmail详细配置（最推荐）

### 1. 开启SMTP服务
- 登录Gmail
- 进入"设置"→"转发和 POP/IMAP"
- 启用 IMAP 或 POP
- 点击"保存更改"

### 2. 开启"允许不够安全的应用"
- 访问: https://myaccount.google.com/secure-sign-in
- 搜索"允许不够安全的应用"
- 选择"启用"

**注意**: 如果您开启了两步验证，需要使用**应用专用密码**:
1. 访问 https://myaccount.google.com/apppasswords
2. 选择"邮件"和"其他(自定义名称)" 
3. 复制生成的16位密码
4. 在 `SMTP_PASSWORD` 中使用这个密码

---

## 🎯 邮件内容示例

### 每日报表邮件
```
📧 主题: A股投资顾问日报 - 2026-04-05

📊 市场概览
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Overall Score: 56.3 (中性)
 Market Trend: 📈 缓慢上涨

BUY信号指数:
  ✅ 科创50 - 强烈买入 (置信度: 82.3%)
  ✅ 中证500 - 买入 (置信度: 68.7%)

SELL信号指数:
  ⚠️ 创业板指 - 观望（风险: 高）

仓位建议:
  - 科创50: 30%
  - 中证500: 25%
  - 沪深300: 15%
  - 现金: 30%
```

---

## 🔍 故障排查

### 问题1: SMTP认证失败
**现象**: `[ERROR] SMTP认证失败`

**解决方案**:
- ✅ 检查邮箱密码是否正确
- ✅ Gmail需要开启"允许不够安全的应用"或使用应用专用密码
- ✅ QQ邮箱需要使用SMTP授权码，不是登录密码

### 问题2: 连接超时
**现象**: `[ERROR] SMTP连接失败: Connection timed out`

**解决方案**:
- ✅ 检查防火墙设置
- ✅ 尝试更换端口（587→465→25）
- ✅ 检查SMTP服务器地址是否正确

### 问题3: 邮件在垃圾邮件
**现象**: 邮件发送成功但收件箱找不到

**解决方案**:
- ✅ 检查垃圾邮件文件夹
- ✅ 将发件人添加到联系人白名单
- ✅ 邮件标题改为更明确的格式

---

## 📊 集成到daily_scheduler.py

修改 `daily_scheduler.py`，添加邮件发送：

```python
from email_client import send_email

def generate_report_and_push_to_feishu(daily_report_path):
    """生成报告并推送（邮件方式）"""
    print("[OK] 生成报告并推送（邮件方式）...")
    
    # 读取报告内容
    with open(daily_report_path, 'r', encoding='utf-8') as f:
        report_content = f.read()
    
    # 构建邮件内容
    subject = f"📧 A股投资顾问日报 - {time.strftime('%Y-%m-%d')}"
    content = f"""
    <h3>📊 A股投资顾问日报</h3>
    <p>日期: {time.strftime('%Y-%m-%d')}</p>
    
    <h4>📈 市场概览</h4>
    <p>市场评分: {score}</p>
    
    <h4>✅ 买入信号</h4>
    <p>{buy_signals}</p>
    
    <h4>⚠️ 卖出信号</h4>
    <p>{sell_signals}</p>
    
    <h4>💰 仓位建议</h4>
    <p>{position_suggestions}</p>
    
    <hr>
    <p><a href="file:///{daily_report_path}">查看完整报告</a></p>
    """
    
    # 发送邮件
    success = send_email(subject, content)
    
    if success:
        print("[OK] 邮件发送成功！")
    else:
        print("[ERROR] 邮件发送失败")
    
    return success
```

---

## 💡 为什么推荐邮件方案？

| 对比项 | 飞书机器人 | 邮件通知 |
|-------|-----------|---------|
| **配置难度** | ⭐⭐⭐⭐⭐ （需要开发者后台配置） | ⭐⭐⭐ （10分钟） |
| **成本** | 免费 | 免费 |
| **稳定性** | ⭐⭐⭐⭐ （依赖API） | ⭐⭐⭐⭐⭐ （SMTP标准） |
| **(收件)可靠性** | ⭐⭐⭐ （需要用户在线） | ⭐⭐⭐⭐⭐ （Inbox保证） |
| **内容 formatting** | ⭐⭐⭐ （纯文本/简单Markdown） | ⭐⭐⭐⭐⭐ （HTML） |
| **历史记录** | ⭐⭐ （聊天记录可能丢失） | ⭐⭐⭐⭐⭐ （邮箱永久保存） |
| **移动端通知** | ⭐⭐⭐ （需要飞书App） | ⭐⭐⭐⭐ （邮箱App推送） |

---

## 🎉 总结

**推荐方案**: 邮件通知  
**理由**: 
1. ✅ 无需机器人权限
2. ✅ 配置简单（10分钟）
3. ✅ 免费可靠
4. ✅ 内容丰富（HTML格式）
5. ✅ 随时随地查看

**步骤**:
1. 准备发件人邮箱（推荐Gmail）
2. 配置SMTP信息
3. 测试邮件发送
4. 集成到daily_scheduler.py

**遇到问题？** 我可以帮您调试！