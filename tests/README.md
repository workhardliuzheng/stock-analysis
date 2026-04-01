# Tests 测试脚本集合

本目录包含股票分析系统的各类测试脚本，按功能分类组织。

## 目录结构

```
tests/
├── __init__.py              # 包初始化
├── README.md                # 本文件
│
├── backtest/                # 回测测试
│   ├── test_all_indices_backtest.py      # 全部指数回测
│   ├── test_multi_index_backtest.py      # 多指数组合回测
│   ├── test_v6_backtest.py               # V6版本回测
│   └── test_v6_backtest_8indices.py      # V6版本8指数回测
│
├── position/                # 仓位管理测试
│   ├── test_v7_position_simple.py        # V7仓位分配简化测试
│   ├── test_v7_position_detailed.py      # V7仓位分配详细测试
│   └── demo_position_manager.py          # 仓位管理器演示
│
└── feature/                 # 特征工程测试
    ├── test_feature_cross.py             # 特征交叉工程测试
    └── test_model_cache.py               # 模型缓存测试
```

## 使用说明

### 运行单个测试

```bash
# 回测测试
python tests/test_v7_position_detailed.py

# 特征工程测试
python tests/test_feature_cross.py
```

### 运行所有测试

```bash
# 批量运行（需要自行编写测试套件）
python -m pytest tests/ -v
```

## 测试分类说明

### 1. 回测测试 (backtest/)

测试不同版本的回测策略效果：

- **test_all_indices_backtest.py**: 全部8个指数的回测
- **test_multi_index_backtest.py**: 多指数组合回测
- **test_v6_backtest.py**: V6版本（激进仓位优化）回测
- **test_v6_backtest_8indices.py**: V6版本8指数全量回测

### 2. 仓位管理测试 (position/)

测试仓位分配策略：

- **test_v7_position_simple.py**: V7版本简化仓位测试
- **test_v7_position_detailed.py**: V7版本详细仓位分析
- **demo_position_manager.py**: 仓位管理器功能演示

### 3. 特征工程测试 (feature/)

测试特征工程和模型优化：

- **test_feature_cross.py**: 特征交叉工程效果测试
- **test_model_cache.py**: 模型缓存和增量预测测试

## 版本对应关系

| 版本 | 主要优化 | 测试文件 |
|------|---------|---------|
| V5 | 基础ML策略 | test_all_indices_backtest.py |
| V6 | 激进仓位优化 | test_v6_backtest*.py |
| V7-1 | 模型持久化 | test_model_cache.py |
| V7-2 | 特征交叉工程 | test_feature_cross.py, test_v7_position*.py |

## 注意事项

1. 测试脚本需要在项目根目录运行，或正确设置 Python 路径
2. 部分测试需要数据库连接，确保 `config.yaml` 配置正确
3. ML相关测试需要安装 xgboost、scikit-learn 等依赖
4. 回测测试耗时较长（5-30分钟），请耐心等待

## 新增测试规范

新增测试脚本时，请遵循以下规范：

1. **命名规范**: `test_<功能>_<描述>.py`
2. **文档字符串**: 文件顶部添加功能说明
3. **导入路径**: 使用 `sys.path.insert(0, '.')` 确保导入正确
4. **输出格式**: 使用统一的表格格式展示结果
5. **错误处理**: 添加 try-except 捕获异常

示例：

```python
"""
测试功能说明

测试目标：xxx
预期效果：xxx
"""

import sys
sys.path.insert(0, '.')

# 测试代码...
```
