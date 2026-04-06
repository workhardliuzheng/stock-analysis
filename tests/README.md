# Tests 目录 - 测试脚本

## 📋 测试文件列表

| 文件 | 说明 |
|------|------|
| `test_dynamic_weight.py` | 动态权重优化测试 |
| `test_report_generation.py` | 报告生成测试 |
| `test_requests.py` | HTTP请求测试 |
| `test_v74_portfolio_backtest.py` | V7-4组合回测测试 |
| `test_v74_signal_optimizer.py` | V7-4信号优化测试 |
| `test_v74_simple.py` | V7-4简单测试 |
| `test_v75_fast.py` | V7-5快速测试 |
| `test_v75_portfolio.py` | V7-5组合测试 |
| `test_v75_quick.py` | V7-5快速验证 |

## 🧪 运行测试

```bash
# 运行所有测试
python -m unittest discover tests

# 运行单个测试
python tests/test_v75_fast.py
```

## 📝 测试覆盖

- ✅ 多因子评分计算
- ✅ ML预测模型
- ✅ 信号融合逻辑
- ✅ 报告生成格式
- ✅ 邮件发送功能

---

## 🧩 _add more tests here
