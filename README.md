# A股指数投资顾问系统 📊

> 基于Tushare数据的A股指数技术分析系统，自动化生成买卖信号。

## 🎯 功能特点

- ✅ **多因子评分**: 5维度综合评分（趋势、动量、成交量、估值、波动率）
- ✅ **ML预测**: XGBoost模型预测上涨概率
- ✅ **自适应融合**: V7-5自动学习最优信号融合权重
- ✅ **组合回测**: 支持多指数组合策略回测
- ✅ **自动日报**: 每日16:00自动生成分析报告并邮件发送
- ✅ **股票/ETF**: 支持指数成分股买卖信号生成

## 📂 项目结构

```
E:\pycharm\stock-analysis\
├── main.py                    # 主程序入口
├── daily_scheduler.py         # 日报调度器（自动执行）
├── weekly_scheduler.py        # 周报调度器
├── sync_main.py               # 数据同步
├── check_factor_scores.py     # 因子得分检查
├── email_client.py            # 邮件客户端
├── report_generator.py        # 报告生成器
│
├── AGENTS.md                  # 开发者说明（Agent配置）
├── TODO.md                    # 待优化项清单（推荐优先阅读）
├── BACKTEST_LOG.md            # 回测与优化日志（所有策略效果）
├── 指标说明.md                 # 投资顾问指标详解（如何用）
├── EMAIL_SETUP.md             # 邮件配置说明
│
├── analysis/                  # 核心分析模块
│   ├── index_analyzer.py      # 指数分析器（主入口）
│   ├── multi_factor_scorer.py # 多因子评分器
│   ├── ml_predictor.py        # ML预测器
│   ├── signal_generator.py    # 信号整合器
│   ├── adaptive_fusion_optimizer.py  # V7-5自适应融合
│   ├── feature_cross_engine.py       # 特征交叉引擎
│   └── ...
│
├── sync/                      # 数据同步模块
│   └── index/
│       └── sixty_index_analysis.py
│
├── scripts/                   # 运行脚本
│   ├── README.md              # 脚本说明
│   ├── record_v75_backtest.py
│   ├── run_portfolio_backtest.py
│   └── run_v74_test.py
│
├── tests/                     # 测试脚本
│   └── README.md              # 测试说明
│
└── records/                   # 回测记录与图表
```

## 🚀 快速开始

### 1. 环境准备

```bash
# Windows虚拟环境
E:
cd E:\pycharm\stock-analysis
python -m venv .venv
Activate.ps1
pip install -r requirements.txt
```

### 2. 配置Tushare Token

编辑 `config.yaml`:

```yaml
tushare:
  token: "YOUR_TUSHARE_TOKEN"
```

### 3. 运行日报任务

```bash
# 快速测试（跳过数据同步）
python daily_scheduler.py --skip-sync

# 正常运行（包含数据同步）
python daily_scheduler.py
```

### 4. 查看信号

```bash
# 查看科创50信号
python main.py --code 000688.SH

# 查看所有指数信号
python main.py
```

## 📋 投资指标说明

| 指标 | 含义 | 操作参考 |
|------|------|---------|
| `final_signal` | 最终信号 | BUY→建仓, SELL→减仓, HOLD→观望 |
| `final_confidence` | 置信度 | 80%+强力信号, <50%谨慎参与 |
| `factor_score` | 多因子评分 | 80+强势上涨, <20强烈卖出 |
| `ml_probability` | ML上涨概率 | 70%+可加仓, <30%考虑清仓 |

**详细说明**: 见 `指标说明.md`

## 📊 回测效果

| 优化版本 | 总收益 | 夏普比率 | 说明 |
|---------|--------|----------|------|
| **V7-5** | **+264.98%** | **1.35** | 自适应融合优化 |
| V7-4 | +2550% (BUY) | 0.82 | 信号阈值优化 |
| V7-2 | +109.97% | - | 特征交叉工程 |

**详细回测**: 见 `BACKTEST_LOG.md`

## 🛠️ 主要优化（TODO.md）

- ✅ V7-5自适应融合优化（+258.24%收益提升）
- ✅ V7-4信号阈值优化（信号频率+183%）
- ✅ 特征交叉工程（+96.36%收益提升）
- ✅ 多因子动态权重优化
- ✅ 仓位管理优化（多指数分散持仓）
- ✅ 止损止盈机制

**完整列表**: 见 `TODO.md`

## 📧 邮件配置

已集成网易邮箱SMTP:

```
SMTP服务器: smtp.163.com
端口: 465 (SSL)
用户名: workhardliuzheng@163.com
授权码: UBnHVwGi2QG3JEA2
```

**配置原理**: 邮件凭证在`EMAIL_SETUP.md`，实际配置在项目内部，不通过CLI参数传递。

## 🧪 测试运行

```bash
# 运行V7-5回测记录
python scripts/record_v75_backtest.py

# 运行多指数组合回测
python scripts/run_portfolio_backtest.py

# 查看测试说明
cat tests/README.md
```

## 📝 Git提交规范

```bash
# 每次优化后必须:
git add -A
git commit -m "feat: [描述优化内容] ( backs test results )"
git push
```

---

## 🎯 下一步优化（TODO.md）

- 🔴 宏观因子（利率、汇率等）
- 🔴 市场状态识别（牛/熊/震荡）
- 🔴 跨指数特征（大盘/小盘联动）
- 🟡 多时间框架联动
- 🟡 信号融合规则优化
- 🔧 Web Dashboard

---

**作者**: Zeno 🧙‍♂️  
**最后更新**: 2026-04-05  
**版本**: V7-5
