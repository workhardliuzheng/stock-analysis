# V7-4 信号阈值优化计划

## 📋 优化目标

当前信号全是"HOLD"（98.2%），需要增加BUY/SELL信号频率，目标：
- BUY/SELL信号比例提升至20-30%
- 组合回测总收益提升

## 🔍 根本原因分析

### 当前状态 (科创50)
```
factor_score范围: 33.60 - 70.60 (宽度仅37)
平均得分: 51.49 (中性水平)
HOLD信号: 98.2% (752/766)
BUY信号: 1.8% (14/766)
SELL信号: 0.0% (0/766)

trend_state分布:
- sideways: 71.3% (震荡市)
- uptrend: 16.1% (牛市)
- downtrend: 12.7% (熊市)
```

### 信号生成规则
```python
# uptrend: score >= 60 → BUY, score < 40 → HOLD
# downtrend: score < 30 → SELL, score >= 70 → HOLD  
# sideways: score >= 65 → BUY, score < 35 → SELL
```

**问题**：当前平均得分51.49在所有状态下面临HOLD信号

## 🛠️ V7-4 优化方案

### 方案1: 调整信号阈值 ⭐⭐⭐⭐⭐

**核心逻辑**：降低信号生成门槛，增加信号频率

#### 默认阈值 vs 优化阈值

```
默认阈值:
- uptrend: BUY >= 60, SELL < 40
- downtrend: BUY >= 70, SELL < 30
- sideways: BUY >= 65, SELL < 35

优化阈值 (方案A):
- uptrend: BUY >= 55, SELL < 45
- downtrend: BUY >= 60, SELL < 35
- sideways: BUY >= 60, SELL < 40

优化阈值 (方案B):
- uptrend: BUY >= 50, SELL < 50
- downtrend: BUY >= 50, SELL < 50
- sideways: BUY >= 55, SELL < 45
```

### 方案2: 引入分数差值阈值 ⭐⭐⭐⭐⭐

**核心逻辑**：当分数接近阈值时，适当降低信号强度，但仍产生信号

```python
# 当前逻辑:
if score >= 65: BUY
elif score < 35: SELL
else: HOLD

# 优化逻辑:
if score >= 62: BUY
elif score > 58: BUY (弱信号)
elif score < 38: SELL
elif score < 42: SELL (弱信号)
else: HOLD
```

### 方案3: 结合评分变化趋势 ⭐⭐⭐⭐⭐

**核心逻辑**：评分快速上升/下降时，即使未达阈值也可产生信号

```python
# 计算评分变化率
score_delta = score - score_prev
score_delta_ratio = score_delta / score_prev

# 引入变化率阈值
if score >= 55 and score_delta > 0.05: BUY
elif score <= 45 and score_delta < -0.05: SELL
else: HOLD
```

### 方案4: 动态阈值调整 ⭐⭐⭐⭐⭐

**核心逻辑**：根据市场波动率调整信号阈值

```python
# 波动率计算
volatility = atr / close * 100

# 动态阈值
if volatility > 2.0:  # 高波动
    BUY_THRESHOLD = 52
    SELL_THRESHOLD = 48
elif volatility > 1.5:  # 中高波动
    BUY_THRESHOLD = 55
    SELL_THRESHOLD = 45
else:  # 低波动
    BUY_THRESHOLD = 58
    SELL_THRESHOLD = 42
```

## 📝 实施计划

### 阶段1: 基础阈值调整 (Day 1)
- [x] 修改multi_factor_scorer.py中的_signal_generate方法
- [ ] 测试科创50信号分布
- [ ] 验证组合回测收益提升

### 阶段2: 高级阈值优化 (Day 2)
- [ ] 实现动态阈值调整
- [ ] 实现评分变化率阈值
- [ ] 组合回测对比各种方案

### 阶段3: 集成ML预测 (Day 3)
- [ ] 结合XGBoost回归预测
- [ ] 动态调整信号强度
- [ ] 最终回测验证

## 🎯 评估指标

| 指标 | 当前 | 目标 | 提升要求 |
|------|------|------|---------|
| BUY信号比例 | 1.8% | 10-15% | ≥500% |
| SELL信号比例 | 0.0% | 5-10% | ≥100% |
| HOLD信号比例 | 98.2% | 75-85% | ≤25% |
| 总收益 | 0.00% | +20-50% | ≥2000% |
| 夏普比率 | 0.0000 | ≥0.3 | ≥0.3 |

## 📊 回测脚本

### 当前回测配置
```python
INDEX_PORTFOLIO = {
    '000688.SH': {'name': '科创50', 'weight': 0.10},
    '399006.SZ': {'name': '创业板指', 'weight': 0.10},
    '000001.SH': {'name': '上证综指', 'weight': 0.15},
    '399300.SZ': {'name': '沪深300', 'weight': 0.20},
    '000905.SH': {'name': '中证500', 'weight': 0.15},
    '399102.SZ': {'name': '深证成指', 'weight': 0.10},
    '000016.SH': {'name': '上证50', 'weight': 0.10},
    '000852.SH': {'name': '中证1000', 'weight': 0.10},
}
```

### 评估方法
```bash
# 测试科创50信号分布
python check_factor_scores.py

# 测试组合回测
python run_portfolio_backtest.py

# 对比不同阈值配置
python test_v74_threshold_optimizer.py (待创建)
```

## ⏰ 时间规划

| 阶段 | 任务 | 预估时间 |
|------|------|---------|
| 阶段1 | 基础阈值调整 | 30分钟 |
| 阶段2 | 高级阈值优化 | 60分钟 |
| 阶段3 | 集成ML预测 | 90分钟 |
| 阶段4 | 回测验证 | 30分钟 |
| **总计** | | **3小时** |

## 📝 备注

- 所有优化必须进行回测验证
- 单指数测试通过后才能组合回测
- 记录每次优化的信号分布和收益变化
- 保持代码可追溯性
