# 完整功能测试指令

## 🧪 测试目标
1. **指数预测功能**: 验证数据分析和信号生成
2. **邮件通知功能**: 验证邮件发送

---

## 📋 测试步骤

### 步骤1: 清理旧数据（可选）
```bash
cd E:\pycharm\stock-analysis
rmdir /s /q data
rmdir /s /q reports
```

### 步骤2: 测试指数预测 + 邮件发送（完整流程）
```bash
python daily_scheduler.py --skip-sync
```

**预期结果**:
1. ✅ 分析12个指数的数据
2. ✅ 生成信号统计
3. ✅ 保存报告到 `reports/daily_report_YYYYMMDD.md`
4. ✅ 邮件发送成功（当前已关闭，见下方启用方法）

### 步骤3: 启用邮件通知功能
编辑 `daily_scheduler.py`，找到下行并**取消注释**：

```python
# 5. 邮件发送报告
scheduler.send_report_by_email(report_path)
```

### 步骤4: 再次测试（包含邮件发送）
```bash
python daily_scheduler.py --skip-sync
```

**预期结果**:
1. ✅ 完整的指数分析
2. ✅ 保存报告文件
3. ✅ 邮件发送成功（检查邮箱收件箱）

---

## 🎯 精简测试（快速）

### 快速测试邮件通知
```bash
python email_client.py --send-report "快速测试邮件通知功能" --subject "[快速测试] 邮件通知"
```

### 快速测试指数分析
```bash
python -c "from daily_scheduler import DailyScheduler; s = DailyScheduler(); results = s.analyze_real_indices(); print('分析完成', len(results), '个指数')"
```

### 快速测试完整流程（跳过数据同步）
```bash
python -c "
from daily_scheduler import DailyScheduler
s = DailyScheduler()
results = s.analyze_real_indices()
report = s.generate_daily_report(results)
path = s.save_report(report, 'TEST')
print('报告保存到:', path)

# 启用邮件发送
success = s.send_report_by_email(path)
print('邮件发送:', '成功' if success else '失败')
"
```

---

## 📊 预期输出示例

```
============================================================
[OK] A股 Daily Scheduler - 2026-04-05
============================================================
[OK] 开始分析真实指数数据...
============================================================
[OK] 分析 上证综指 (000001.SH)...
[OK] 分析 深证成指 (399001.SZ)...
[OK] 分析 创业板指 (399006.SZ)...
...
[OK] 所有指数分析完成
[OK] 生成日报内容...
[OK] 保存报告到文件...
[OK] 报告已保存到: E:\pycharm\stock-analysis\reports\daily_report_20260405.md
[OK] 报告生成成功！
[OK] 通过邮件发送报告...
[OK] 邮件发送成功！
============================================================
[OK] 任务执行完成
============================================================
```

---

## 🔍 故障排查

### 问题1: 邮件发送失败
**检查**:
1. SMTP配置是否正确（`email_client.py`）
2. 网易邮箱授权码是否有效
3. 网络连接是否正常

**测试**:
```bash
python email_client.py --test
```

### 问题2: 分析失败
**检查**:
1. MySQL连接是否正常
2. Tushare数据是否同步
3. 分析模块是否安装

**测试**:
```bash
python -c "from sync.index.sixty_index_analysis import SixtyIndexAnalysis; a = SixtyIndexAnalysis('000001.SH'); print('模块加载成功')"
```

### 问题3: 导入错误
**解决**:
```bash
cd E:\pycharm\stock-analysis
set PYTHONPATH=%CD%;%PYTHONPATH%
python your_script.py
```

---

## 📝 推荐测试顺序

1. **先测试邮件通知** (5分钟)
   ```bash
   python email_client.py --test
   ```

2. **再测试快速分析** (10分钟)
   ```bash
   python -c "from daily_scheduler import DailyScheduler; s = DailyScheduler(); results = s.analyze_real_indices(); print('成功分析', len(results), '个指数')"
   ```

3. **最后测试完整流程** (30分钟)
   ```bash
   python daily_scheduler.py --skip-sync
   ```

---

## ✅ 通过标准

- ✅ 邮件测试: 收到("[测试邮件] A股投资顾问系统")
- ✅ 指数分析: 分析12个指数成功
- ✅ 邮件发送: 收到报告邮件
- ✅ 报告生成: `reports/daily_report_*.md` 文件存在

祝测试顺利！📈