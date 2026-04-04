# 股市数据同步与信号生成

> **技能ID**: `stock_analysis_signal_generator`  
> **版本**: v1.1  
> **最后更新**: 2026-04-04  
> **类型**: 自动化任务  
> **描述**: 自动同步指数数据并生成买卖信号（内部使用）  
> **公开状态**: ⚠️ 私有技能（不建议公开分享）

---

## 功能概述

本技能用于自动化股市数据同步与信号生成，包含：

- 📥 **数据同步**: 从Tushare同步指数数据到本地数据库
- 📊 **信号计算**: 基于多因子模型 + XGBoost计算买卖信号
- 📤 **结果输出**: 生成信号报告和投资建议

注意: Tushare Token已配置在项目配置文件中，无需在命令行指定。

---

## 使用场景

- **定时任务**: 每日4:00自动同步数据并生成信号
- **按需执行**: 手动触发数据同步或信号计算
- **多指数支持**: 支持单个或多个指数的同时分析

---

## 命令行接口

### 基础用法

```bash
copaw skills run stock_analysis_signal_generator ^
  --agent-id <agent-id>
```

注意: Tushare Token已配置在项目配置文件中，无需额外指定。

### 仅同步数据

```bash
copaw skills run stock_analysis_signal_generator ^
  --agent-id <agent-id> ^
  --data-only
```

### 仅计算信号

```bash
copaw skills run stock_analysis_signal_generator ^
  --agent-id <agent-id> ^
  --signal-only
```

### 指定指数

```bash
copaw skills run stock_analysis_signal_generator ^
  --agent-id <agent-id> ^
  --indices "000688.SH,399006.SZ"
```

### 执行投资顾问报告

```bash
copaw skills run stock_analysis_signal_generator ^
  --agent-id <agent-id> ^
  --advisor
```

### 执行信号分析报告

```bash
copaw skills run stock_analysis_signal_generator ^
  --agent-id <agent-id> ^
  --report
```

---

## 参数说明

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `--agent-id` | 是 | Agent标识符 | `--agent-id default` |
| `--indices` | 否 | 指数代码（逗号分隔） | `--indices "000688.SH,399006.SZ"` |
| `--start-date` | 否 | 数据起始日期 | `--start-date 20230101` |
| `--data-only` | 否 | 仅执行数据同步 | `--data-only` |
| `--signal-only` | 否 | 仅执行信号计算 | `--signal-only` |
| `--advisor` | 否 | 生成投资顾问报告 | `--advisor` |
| `--report` | 否 | 生成信号分析报告 | `--report` |

注意: Tushare Token已配置在项目配置文件中，无需额外指定。

---

## 返回结果

### 控制台输出

```
================================================================================
[OK] 股市分析系统 - 信号生成
[OK] 生成时间: 2026-04-04 17:16:24
================================================================================

[OK]【市场概览】
-震荡偏空
-交易量: 中等
-市场情绪: 谨慎

[OK]【核心结论】
[OK] 强烈看跌: 平均信号强度 -33.5
   建议仓位: 10-20%
   策略: 大幅减仓/空仓观望
...
```

### 文件输出

- 多因子信号: `signals/{指数代码}_signals.csv`
- 投资报告: `report/{日期}_signal_report.md`

---

## 配置文件

**配置路径**: `active_skills/stock_signal_generator/config.yaml`

**关键配置项**:
```yaml
tushare:
  token: YOUR_TUSHARE_TOKEN_HERE
  date_format: "%Y-%m-%d"

indices:
  - code: "000688.SH"
    name: "科创50"
    weight: 0.20
  - code: "399006.SZ"
    name: "创业板指"
    weight: 0.20
  # ... 更多指数

backtest:
  start_date: "2023-01-01"
  transaction_cost: 0.0006

signal:
  strategy: "v7.5"
  threshold_strategy: "aggressive_lite"
```

---

## 定时任务

**执行时间**: 每天4:00自动运行

```bash
copaw cron create ^
  --name "stock_signal_generator" ^
  --schedule "0 4 * * *" ^
  --command "copaw skills run stock_analysis_signal_generator --agent-id default --tushare-token YOUR_TOKEN" ^
  --agent-id default
```

---

## 输出示例

### 核心结论

```
强烈看跌: 平均信号强度 -33.5
   建议仓位: 10-20%
   策略: 大幅减仓/空仓观望
```

### 指数建议

```
1. 创业板指 (399006.SZ)
-当前信号: HOLD | 持仓
-信号强度: -4.7
-操作建议: 观望/波段
-建议仓位: 30-40%

2. 科创50 (000688.SH)
-当前信号: SELL | 卖出
-信号强度: -25.2
-操作建议: 大幅减仓/空仓
-建议仓位: 0-10%
```

---

## 错误处理

### 常见错误

| 错误 | 解决方案 |
|------|----------|
| `UnicodeEncodeError` | 已修复 - 使用ASCII字符代替emoji |
| `ModuleNotFoundError` | 确保`pandas`和`numpy`已安装 |
| `API Error` | 检查Tushare Token是否有效 |

---

## 技术细节

- **信号策略**: V7-4 aggressive_lite + V7-5自适应融合
- **回测引擎**: 支持T+1收盘价/开盘价执行
- **数据源**: Tushare Pro API
- **模型**: XGBoost + Optuna超参数调优

---

## 注意事项

- 项目已内置Tushare Token配置，无需在命令行指定
- 建议配置定时任务而非频繁手动执行
- 输出文件保存在项目目录的`signals/`和`report/`下
- 本Skill为内部使用，不建议公开分享
