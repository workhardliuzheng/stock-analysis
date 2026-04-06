# Scripts 目录 - 运行脚本

## 📋 快速导航

| 脚本 | 用途 | 说明 |
|------|------|------|
| `record_v75_backtest.py` | 记录V7-5回测结果 | 已完成回测，记录最优权重 |
| `run_portfolio_backtest.py` | 多指数组合回测 | 回测组合策略收益 |
| `run_v74_test.py` | V7-4阈值测试 | 测试信号阈值优化效果 |

## 🚀 常用命令

```bash
# V7-5回测结果记录
python scripts/record_v75_backtest.py

# 多指数组合回测
python scripts/run_portfolio_backtest.py

# V7-4阈值测试
python scripts/run_v74_test.py
```

## 📊 回测成果

- **V7-5最优权重**（科创50，Walk-Forward验证）:
  - factor_score: 73.58%
  - ml_return: 16.79%
  - ml_signal: 5.68%
  - factor_signal: 3.94%
- **组合总收益**: +264.98% (从+73.97%提升)

---

## 🎯 _add more scripts here
