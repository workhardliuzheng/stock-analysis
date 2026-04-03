# 📈 股票分析系统 Skill 配置

> 配置文件: 2026-04-03

## Skill 信息

- **Name**: stock_analysis_signal_generator
- **Description**: 股票分析系统 - 自动化信号生成
- **Version**: 1.0.0
- **Author**: Zeno

## 安装说明

1. 将 `stock_signal_generator` 文件夹放入 CoPaw 的 `active_skills` 目录
2. 确保项目依赖已安装:
```bash
pip install tushare pandas numpy xgboost scikit-learn optuna
```

## 运行方式

### 基础命令

```bash
# 完整执行 (数据同步 + 信号计算)
copaw skills run stock_analysis_signal_generator --agent-id <agent-id> --tushare-token YOUR_TOKEN

# 仅同步数据
copaw skills run stock_analysis_signal_generator --agent-id <agent-id> --tushare-token YOUR_TOKEN --data-only

# 仅计算信号
copaw skills run stock_analysis_signal_generator --agent-id <agent-id> --tushare-token YOUR_TOKEN --signal-only
```

### 直接运行

```bash
# 完整执行
python run_signal_generator.py --tushare-token YOUR_TOKEN

# 仅同步数据
python sync_data.py --tushare-token YOUR_TOKEN

# 仅计算信号
python calculate_signals.py --tushare-token YOUR_TOKEN
```

## 定时任务配置

在 CoPaw CLI 中创建定时任务:

```bash
copaw cron create \
  --name "daily_stock_signal" \
  --schedule "0 4 * * *" \
  --command "copaw skills run stock_analysis_signal_generator --agent-id <agent-id> --tushare-token YOUR_TOKEN" \
  --agent-id <agent-id>
```

或者手动配置 cron 任务 (crontab):

```bash
# 编辑 crontab
crontab -e

# 添加以下行 (每天4:00运行)
0 4 * * * python E:\pycharm\stock-analysis\active_skills\stock_signal_generator\run_signal_generator.py --tushare-token YOUR_TOKEN >> E:\pycharm\stock-analysis\logs\cron.log 2>&1
```

## 配置参数

| 参数 | 说明 | 默认值 | 必填 |
|------|------|--------|------|
| `--tushare-token` | Tushare Pro API Token | - | ✅ |
| `--data-only` | 仅执行数据同步 | false | ❌ |
| `--signal-only` | 仅执行信号计算 | false | ❌ |
| `--indices` | 指数代码列表 | 5个默认指数 | ❌ |
| `--start-date` | 数据起始日期 | 20230101 | ❌ |

## 默认指数列表

```
000688.SH   - 科创50
399006.SZ   - 创业板指
000001.SH   - 上证综指
000905.SH   - 中证500
000852.SH   - 中证1000
```

## 输出文件

- **日志**: `E:\pycharm\stock-analysis\logs\`
- **信号**: `E:\pycharm\stock-analysis\signals\`
- **报告**: `E:\pycharm\stock-analysis\report\`

## 错误处理

常见错误:
1. **Tushare Token 无效**: 检查 Token 是否正确
2. **网络连接失败**: 检查网络和 firewall
3. **数据为空**: 检查指数代码是否正确

## 更新日志

- **v1.0.0** (2026-04-03)
  - ✅ 完整数据同步功能
  - ✅ 多因子信号计算 (V7-4优化)
  - ✅ 融合信号生成 (V7-5优化)
  - ✅ 定时任务支持
