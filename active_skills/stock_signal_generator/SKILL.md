# 项目Skill - 股市分析系统信号生成

> 技能ID: `stock_analysis_signal_generator`
> 版本: v1.0
> 最后更新: 2026-04-03

## 功能说明

本技能提供自动化股市信号生成功能，包含：

1. **数据同步**: 自动同步指数数据（Tushare Pro API）
2. **计算信号**: 多因子模型 + XGBoost机器学习融合信号
3. **信号输出**: 生成买卖信号并保存结果

## 使用方法

### 基础执行

```bash
copaw skills run stock_analysis_signal_generator --agent-id <agent-id>
```

### 带参数执行

```bash
copaw skills run stock_analysis_signal_generator --agent-id <agent-id> ^
  --data-only ^
  --signal-only ^
  --indices "000688.SH,399006.SZ"
```

## 参数说明

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `--data-only` | 否 | 仅执行数据同步 | `--data-only` |
| `--signal-only` | 否 | 仅执行信号计算 | `--signal-only` |
| `--indices` | 否 | 指定指数代码（逗号分隔） | `--indices="000688.SH,399006.SZ"` |
| `--start-date` | 否 | 数据起始日期 | `--start-date=20230101` |
| `--tushare-token` | 是 | Tushare Pro API Token | `--tushare-token=YOUR_TOKEN` |

## 返回结果

```
✅ [数据同步]
   - 科创50: 766行数据
   - 创业板指: 781行数据
   - 上证综指: 781行数据
   - 中证500: 766行数据
   - 中证1000: 766行数据

✅ [信号计算]
   - 多因子评分: 完成
   - ML预测: MAE=0.75, RMSE=1.08
   - 融合信号: V7-5自适应优化
   - 组合总收益: +264.98%

✅ [输出文件]
   - signals/000688.SH_signals.csv
   - signals/399006.SZ_signals.csv
   - report/2026-04-03_signal_report.md
```

## 定时任务配置

每天4:00自动运行：

```bash
copaw cron create ^
  --name "stock_signal_generator" ^
  --schedule "0 4 * * *" ^
  --command "copaw skills run stock_analysis_signal_generator --agent-id <agent-id> --tushare-token YOUR_TOKEN" ^
  --agent-id <agent-id>
```

## 错误处理

遇到错误时：
1. 检查Tushare API Token是否有效
2. 确认网络连接正常
3. 查看日志文件获取详细错误信息

## 日志文件

- 错误日志: `logs/error.log`
- 运行日志: `logs/run.log`
- 数据日志: `logs/data_sync.log`

## 格式要求

- 指数代码: 6位数字 + 后缀.SH/.SZ
- 日期格式: YYYYMMDD
- 时间格式: HH:MM (24小时制)
