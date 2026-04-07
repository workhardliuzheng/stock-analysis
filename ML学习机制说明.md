# ML学习机制说明

## 📊 学习机制详解

### 1. 训练数据量

```
初始化训练窗口: 500条数据 (~2年)
滚动测试窗口: 60条数据 (~1季度)
```

**实际训练过程**:
- **第1次训练**: 数据范围 0~499 (2021-04~2023-03) → 预测第500天
- **第2次训练**: 数据范围 0~500 (增加1天) → 预测第501天
- **第30次训练**: 数据范围 0~529 (每30天重新训练) → 预测第530天

**总结**: 每次预测使用**截至当日的历史数据**，共约500条（2年）

### 2. 是否会继续学习新数据？

**是！使用Walk-Forward滚动学习机制！**

```python
# 关键代码
train_indices = valid_indices[:i]  # 所有历史数据
model.fit(X_train, y_train)         # 重新训练模型
```

**学习流程**:
1. 每天预测前，用截止到当天的所有历史数据重新训练模型
2. 从500条数据开始，逐日增加至全部可用数据
3. 每30天重新训练一次（减少计算量）

**示例**（科创50 1246条数据）:
- 第1次训练: 500条 → 预测第501天
- 第30次训练: 530条 → 预测第531天
- ...
- 第40次训练: 746条 (全部数据) → 预测最后几天

### 3. 新数据进来会自动学习吗？

**不会！需要手动运行！**

**原因**:
- ML模型训练只在`IndexAnalyzer.analyze()`时执行
- 不是实时learning系统
- **需要定期运行才能更新模型**

**使用方式**:
```bash
# 每天运行更新模型
python daily_scheduler.py

# 或单独运行
python main.py --code 000688.SH
```

### 4. 模型保存与加载

当前策略: **不保存模型，每次重新训练**

```python
# 说明文档中的方法
predictor.save_model('models/000300.pkl')
predictor.load_model('models/000300.pkl')
```

但实际代码中**未调用保存功能**，每次运行都重新训练。

### 5. 预测逻辑

```python
# 滚动预测（避免数据泄露）
for i, idx in enumerate(valid_indices):
    # 只用 idx 之前的数据训练
    train_indices = valid_indices[:i]
    model.fit(X_train, y_train)
    
    # 预测 idx 位置的收益
    pred = model.predict(X_pred)
```

---

## 🔍 技术细节

### 特征工程
- 输入: ~35个技术指标特征
- 输出: 次日收益率预测
- 标签: `pct_chg/100` (实际收益率)

### 验证方式
- Walk-Forward滚动验证
- 无数据泄露
- 预测指标:
  - **MAE**: 平均绝对误差
  - **RMSE**: 均方根误差
  - **方向准确率**: 预测涨跌方向正确率
  - **IC**: 信息系数（预测值与真实值相关性）

### 信号生成
```python
# 将预测收益率转换为信号
sigmoid(value * scale + offset) → 概率
sigmoid(ml_predicted_return *return_std) → ml_probability

# 最终信号
if ml_probability > 0.5 → BUY
if ml_probability < 0.5 → SELL
```

---

## 📝 总结

| 项目 | 说明 |
|------|------|
| 训练数据 | ~500条（2年历史） |
| 学习方式 | Walk-Forward滚动学习 |
| 新数据处理 | 需手动运行更新模型 |
| 模型保存 | 暂未启用 |
| 预测更新 | 每次运行`main.py`或`daily_scheduler.py` |

**使用建议**:
- 每天16:00运行`daily_scheduler.py`更新模型
- 确保数据同步完成后再运行
- ML模型会自动学习最新数据模式
