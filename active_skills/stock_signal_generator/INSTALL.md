# Copaw Skill 安装说明

## 问题：导入Skill后页面未看到

### 原因分析

1. **.copaw-skill 文件缺失** - 这是Copaw识别Skill的必要文件
2. **ZIP包未包含隐藏文件** - Windows默认不显示隐藏文件
3. **Copaw技能目录未刷新** - 需要重启Copaw服务

### 解决方案

#### 方案1: 使用正确打包的ZIP包（推荐）

已为您创建了正确的ZIP包：
- 路径: `E:\pycharm\stock-analysis\active_skills\stock_signal_generator.zip`
- 包含13个文件（包括`.copaw-skill`）

**步骤**:
1. 删除Copaw中已导入的旧版本（如果存在）
2. 上传新的ZIP包
3. 等待Copaw完全加载
4. 刷新页面或重启Copaw服务

#### 方案2: 手动安装

**步骤**:
1. 解压缩ZIP包到Copaw的skills目录
   - 通常路径: `C:\Users\<用户名>\.copaw\workspaces\default\active_skills`
2. 确保目录结构为:
   ```
   active_skills/stock_signal_generator/
   ├── .copaw-skill
   ├── SKILL.md
   ├── package.json
   ├── ...
   ```
3. 重启Copaw服务（或重新加载技能）

#### 方案3: 检查Copaw配置

检查Copaw的技能目录配置是否正确：

```bash
copaw config get skills.path
```

如果路径不正确，设置正确的路径：
```bash
copaw config set skills.path "C:\Users\<用户名>\.copaw\workspaces\default\active_skills"
```

## 验证Skill是否启用

### 方法1: Copaw Web UI
- 访问: `http://localhost:3000/skills`
- 查找: `stock_analysis_signal_generator`

### 方法2: 命令行
```bash
copaw skills list
```

如果有输出包含 `stock_analysis_signal_generator`，说明已成功启用。

### 方法3: 尝试运行
```bash
copaw skills run stock_analysis_signal_generator --agent-id default
```

## 常见问题

### Q: 上传ZIP后技能未显示？
A: 可能需要重启Copaw服务：
```bash
copaw restart
```
或手动重启Copaw进程。

### Q: 权限问题？
A: 确保Copaw有权限读取skills目录：
```bash
icacls "C:\Users\<用户名>\.copaw" /grant Everyone:(OI)(CI)F
```

### Q: Windows压缩包不包含隐藏文件？
A: 使用PowerShell或7-Zip重新打包：
```powershell
# 使用 PowerShell (包含隐藏文件)
Compress-Archive -Path E:\pycharm\stock-analysis\active_skills\stock_signal_generator\* -DestinationPath stock_signal_generator.zip -Force

# 使用 7-Zip (更可靠)
"C:\Program Files\7-Zip\7z.exe" a -tzip stock_signal_generator.zip E:\pycharm\stock-analysis\active_skills\stock_signal_generator\*
```

## 技能信息

- **Skill ID**: `stock_analysis_signal_generator`
- **版本**: v1.1.0
- **描述**: 自动化股市数据同步与信号生成（内部使用）
- **类型**: 私有Skill

## 依赖要求

Skill运行需要以下Python包：
- tushare
- pandas
- numpy
- xgboost
- scikit-learn
- optuna

请确保这些包已安装在Copaw的Python环境中。
