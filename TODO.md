# Stock-Analysis 待优化项清单



> 记录系统后续可优化方向，按优先级分类，便于逐步推进。

> 

> ⚠️ **重要**: 每次优化后必须进行回测验证，并更新本文件状态！

> 

> 📝 **2026-04-07更新**: 完成项目整合，统一入口`main.py`支持`daily_report`模式



---



## 📊 当前进度



| 类别 | 数量 | 状态 |

|------|------|------|

| **已实现** | 31项 | ✅ 已完成并验证 |

| **待实现** | 2项 | ⏳ 计划中 |

| **总计** | 30项 | - |



---



## 🎯 第一部分：已实现优化（23项）



### ✅ V9 智能仓位管理 (2026-04-11)

- **文件**: `analysis/smart_position_manager.py` (新建), `analysis/portfolio_backtester.py`, `analysis/backtester.py`, `analysis/index_analyzer.py`, `main.py`

- **测试**: `tests/test_smart_position_manager.py` (25个测试用例)

- **问题**: V8使用二元仓位(0/1)，买卖信号质量差(29-40%胜率, 39-45%卖在局部低点)

- **方案**: 连续仓位(0.0~1.0) + 6大特性(信号确认/RSI过滤/最小持仓期/移动止损/渐进仓位/分批建仓) + 6种regime状态动态参数

- **效果**: 总收益+68.54% (vs V8 +52.68%), 夏普0.46 (vs 0.38), 回撤-36.50% (vs -43.84%), 超额+38.46%

- **CLI**: `python main.py backtest --smart-position`

- **回测**: 见 `BACKTEST_LOG.md #16`



### ✅ V8 市场状态识别 (2026-04-11)

- **文件**: `analysis/market_regime_detector.py` (新建), `index_analyzer.py`, `adaptive_fusion_optimizer.py`, `multi_factor_scorer.py`, `ml_predictor.py`

- **问题**: V7-7的4个共识指标高度相关，BUY/SELL比1:2.45严重偏SELL，所有市场环境使用相同参数

- **方案**: 6状态市场环境识别(BULL_TREND/BULL_LATE/BEAR_TREND/BEAR_LATE/HIGH_VOL/SIDEWAYS) + 3维评分(趋势/波动/情绪) + 动态共识阈值 + 动态因子权重 + ML新增3个regime特征

- **效果**: 超额收益+22.60% (vs V7-7的+4.23%), BUY/SELL比从0.46改善到1.03, 月度胜率50%

- **回测**: 见 `BACKTEST_LOG.md #15`



### ✅ V7-7 多指标共识投票 (2026-04-11)

- **文件**: `analysis/adaptive_fusion_optimizer.py`

- **问题**: 2023年买入后直到2025年才有卖出信号，中间2年无法躲避大跌

- **方案**: 4指标共识投票 (MA+MACD+RSI+ADX)，非对称阈值 (看涨需4票全部同意，看跌仅需3票)

- **效果**: 组合收益 +27.84% vs 基准 +23.60%，超额+4.23%，夏普0.44 vs 0.33

- **回测**: 见 `BACKTEST_LOG.md #14`



### ✅ V7-5 自适应融合优化 (2026-04-03)

- **文件**: `analysis/adaptive_fusion_optimizer.py`

- **效果**: 组合总收益 +264.98% (从+73.97%提升+258.24%)

- **最优权重**: factor_score 73.58%, ml_return 16.79%, ml_signal 5.68%, factor_signal 3.94%

- **信号频率**: 27.7% → 73.1%

- **回测**: 见 `BACKTEST_LOG.md #12`



### ✅ V7-4 信号阈值优化 (2026-04-01)

- **文件**: `analysis/signal_threshold_optimizer.py`

- **效果**: BUY/SELL信号频率从1.8%提升至78.5%

- **回测**: 见 `BACKTEST_LOG.md #11`



### ✅ V7-2 特征交叉工程 (2026-04-01)

- **文件**: `analysis/feature_cross_engine.py`

- **效果**: 科创50 ML收益 +109.97%

- **回测**: 见 `BACKTEST_LOG.md #8`



### ✅ V7-1 模型持久化 (2026-03-30)

- **文件**: `analysis/model_cache.py`

- **效果**: 信号执行速度提升10倍



### ✅ 多因子动态权重优化 (V7-3)

- **文件**: `analysis/multi_factor_scorer.py`, `analysis/dynamic_weight_optimizer.py`

- **效果**: 科创50最优权重验证，夏普比率 0.78

- **回测**: 见 `BACKTEST_LOG.md #9`



### ✅ 其他优化

- 超参数自动调优 (Optuna)

- 特征重要性筛选 (35→20特征)

- 止损止盈机制

- 仓位管理优化

- 标签工程改进 (回归目标)

- 市场择时



---



## 🎯 第二部分：待实现优化（5项）



### 🔴 高价值优化（2项）



#### 1. ✅ 宏观因子 ⭐⭐⭐⭐ (V13已完成)

- **V13方案**: 4源宏观数据(Shibor/北向资金/融资融券/汇率) -> 宏观评分(0-100) -> regime第4维度偏置

- **效果**: 总收益+70.62% (vs V12 +61.89%), 回撤-23.31% (vs -25.23%), 夏普0.51 (vs 0.46)

- **涉及文件**: `analysis/macro_factor_collector.py`, `analysis/macro_factor_scorer.py`, `analysis/market_regime_detector.py`, `analysis/index_analyzer.py`, `main.py`

- **回测**: 见 `BACKTEST_LOG.md #21`



#### 2. ✅ 跨指数特征 ⭐⭐⭐⭐⭐ (V15已完成)

- **现状**: 每个指数独立分析，不考虑其他指数信息

- **方案**: 

  - 大盘指数（上证综指、沪深300）趋势作为小盘指数输入特征

  - 大盘/小盘相对强度（如中证500/沪深300比值趋势）

  - 市场风格轮动信号

- **效果**: 深证成指负贡献翻正(+1.54%)，沪深300接近翻正(-0.24%)

- **涉及文件**: `analysis/ml_predictor.py` (添加跨指数特征方法), `analysis/index_analyzer.py`

- **难度**: 中低 (效果已验证)

- **回测**: 见 `BACKTEST_LOG.md #23`



#### 3. ✅ 多模型集成投票 ⭐⭐⭐⭐⭐ (V15已完成)

- **现状**: ML预测使用单模型，随机种子导致每次结果不同

- **方案**: Walk-Forward每个fold训练5个不同随机种子(42,100,200,300,500)的XGBoost模型，预测取平均值

- **效果**: ML指标大幅改善(沪深300 IC从-0.022→-0.001不再触发反转模式)，两次独立运行结果完全一致

- **涉及文件**: `analysis/ml_predictor.py`

- **回测**: 见 `BACKTEST_LOG.md #23`

### 🟡 中价值优化（2项）



#### 4. ✅ 多时间框架联动 ⭐⭐⭐ (V16已完成)

- **现状**: 仅使用日线数据，震荡市假信号多

- **方案**: 周线MA5/MA10趋势作为过滤条件，bearish周线阻止BUY，strong_bearish周线强制退出

- **效果**: 回撤从-30.51%降至**-22.35%**(改善8.16pp)，收益仅微降0.73%(+56.93%)

- **涉及文件**: `analysis/index_analyzer.py` (_apply_weekly_filter), `analysis/signal_generator.py`

- **回测**: 见 `BACKTEST_LOG.md #24`



#### 5. ⏳ 信号融合规则优化 ⭐⭐⭐

- **现状**: 固定if-else逻辑

- **方案**: 用ML学习最优融合规则

- **预期效果**: 提高信号质量

- **涉及文件**: `analysis/signal_generator.py`

- **难度**: 中等



### 🔧 工程优化（2项）



#### 6. ⏳ Web Dashboard ⭐⭐⭐⭐

- **现状**: 仅命令行输出

- **方案**: Streamlit搭建Web界面

- **预期效果**: 提升用户体验

- **难度**: 中等



### 🟠 V8/V9后续改进（3项）



#### 7. ✅ 动态止损/回撤控制 ⭐⭐⭐⭐ (V9已实现)

- **V9方案**: SmartPositionManager实现regime动态止损(ATR倍数3-5x)

- **效果**: 回撤从-43.84%改善到-36.50%, 夏普0.46



#### 8. ✅ V12 三层下跌保护优化 ⭐⭐⭐⭐⭐ (V12已完成)

- **问题**: V10回撤-35.88%，V11证明纯仓位管理上限为20.6%改善

- **方案**: 
  - L3: 共识阈值放松 (SIDEWAYS/HIGH_VOL bear_thresh -3->-2)
  - L2a: BEAR_TREND阈值扩大 (trend_max 35->40, vol_max 65->70)
  - L2b: 趋势动量偏置 (_apply_momentum_bias, threshold=-25, trend<35)
  - L1: 跨指数趋势共识 (_apply_cross_index_consensus, 5/6/7级缩放)

- **效果**: 回撤-35.88%->-25.23%(改善41.1%), 收益+69.94%->+61.89%(-8.05%), 夏普0.46不变

- **涉及文件**: `analysis/market_regime_detector.py`, `analysis/portfolio_backtester.py`, `analysis/index_analyzer.py`, `main.py`

- **回测**: 见 `BACKTEST_LOG.md #20`



#### 9. ⏳ Regime状态特征增强 ⭐⭐⭐ (待实施)

- **现状**: ML仅使用3个regime维度分数作为特征

- **方案**: 
  - 增加regime持续时长特征（连续同一状态天数）
  - 增加regime转换概率特征（状态转移矩阵）
  - 增加跨指数regime一致性特征（大盘/小盘一致性）

- **预期效果**: 提升ML预测能力5-10%，方向准确率53.69%→58%+

- **涉及文件**: `analysis/market_regime_detector.py`, `analysis/ml_predictor.py`

- **难度**: 中等



---



## 🟢 最近完成（2026-04-19）



### ✅ V14 防鞭打增强优化 (2026-04-19)

- **文件**: `analysis/smart_position_manager.py`

- **问题**: 下跌段频繁止损-重入(鞭打效应)，688天下跌期133次操作，仓位在0%-100%间剧烈震荡

- **方案**: 2个新特性 - 累计止损衰减冷却(近期止损越多冷却期越长，达阈值进入观望模式) + Regime入场禁令(止损后等待regime等级改善才允许再入场)

- **效果**: 总收益+70.62%->+80.39%(+9.77%), 回撤-23.31%->-21.21%(改善2.10pp), 超额+40.54%->+50.31%

- **回测**: 见 `BACKTEST_LOG.md #22`



### ✅ V13 宏观因子影响 (2026-04-18)

- **文件**: `analysis/macro_factor_collector.py` (新建), `analysis/macro_factor_scorer.py` (新建), `analysis/market_regime_detector.py`, `analysis/index_analyzer.py`, `main.py`

- **问题**: V12仅使用技术面+估值数据，缺乏宏观环境感知

- **方案**: 4源宏观数据采集(Shibor/北向资金/融资融券/汇率) + 4维评分器(利率/资金流向/杠杆/汇率) + regime第4维宏观偏置

- **关键发现**: 宏观因子不应直接作为ML特征(会改变模型导致信号漂移)，应仅通过regime检测间接影响

- **效果**: 总收益+61.89%->+70.62%(+8.73%), 回撤-25.23%->-23.31%(改善7.6%), 夏普0.46->0.51

- **回测**: 见 `BACKTEST_LOG.md #21`



### ✅ V12 三层下跌保护优化 (2026-04-18)

- **文件**: `analysis/market_regime_detector.py`, `analysis/portfolio_backtester.py`, `analysis/index_analyzer.py`, `main.py`

- **问题**: V10回撤-35.88%，V11证明纯仓位管理改善上限为20.6%

- **方案**: 三层防护 - L3共识阈值放松 + L2a/L2b动量偏置早期识别 + L1跨指数趋势共识(组合级缩仓)

- **4轮调优**: R1(+13.81%过度保护) -> R2(+24.09%) -> R3(+62.06%禁用L1验证) -> R4(+61.89%/-25.23%最优)

- **效果**: 回撤-35.88%->-25.23%(改善41.1%突破结构性上限)，收益+69.94%->+61.89%(-8.05%)，夏普0.46不变

- **回测**: 见 `BACKTEST_LOG.md #20`



### ✅ V11 避跌优化 (2026-04-13)

- **文件**: `analysis/smart_position_manager.py`, `analysis/portfolio_backtester.py`

- **问题**: V10下跌捕获率73.1%，回撤改善仅16.3%，主下跌期(2021-2024)以SIDEWAYS+BEAR_LATE为主，止损鞭打率24%

- **方案**: 3个新特性 - 自适应止损紧缩(close<MA50时收紧ATR倍数) + 止损后再入场冷却期(2-5天) + MA50趋势过滤(仅熊市/震荡启用，限仓0.4-0.65)

- **3轮调优**: R1全局激进(收益-8.4%回撤更差) -> R2选择性保护(收益-3.9%回撤改善) -> R3加强关键regime

- **效果**: 回撤-35.88%->-34.04%(改善从16.3%提升到20.6%)，收益+69.94%->+65.84%(-4.10%)

- **结论**: 40%回撤改善目标通过纯仓位管理不可达，20.6%是当前框架结构性上限

- **回测**: 见 `BACKTEST_LOG.md #19`



### ✅ V10.1 信号-回测解耦 (2026-04-12)

- **文件**: `analysis/portfolio_backtester.py` (修改 `_load_all_indices()`)

- **问题**: 不同回测起始日期产生不同信号，信号生成依赖DataFrame长度（ML训练数据量、fused_score归一化范围等）

- **方案**: 始终从 `HISTORY_START_DATE_MAP` 加载全量历史数据生成信号，回测区间仅控制交易仿真起止

- **效果**: 子区间(20230401-20241001)超额收益从负值改善为+0.30%，全量回测+64.56% (基本恢复V10水平)

- **回测**: 见 `BACKTEST_LOG.md #18`



### ✅ V9 智能仓位管理 (2026-04-11)

- **文件**: `analysis/smart_position_manager.py` (新建, 520行), `tests/test_smart_position_manager.py` (25测试)

- **6大特性**: 信号确认 + RSI过滤 + 最小持仓期 + 移动止损 + 渐进仓位 + 分批建仓

- **效果**: +68.54% (vs V8 +52.68%), 夏普0.46, 回撤-36.50%

- **回测**: 见 `BACKTEST_LOG.md #16`



### ✅ V7-7 多指标共识投票 (2026-04-11)

- **文件**: `analysis/adaptive_fusion_optimizer.py` (lines 295-369)

- **问题**: 2023年买入后直到2025年才有卖出信号，中间2年无法躲避大跌

- **方案**: 4指标共识投票 (MA+MACD+RSI+ADX)，非对称阈值 (看涨需4票，看跌需3票)

- **效果**: 组合收益 +27.84% vs 基准 +23.60%，夏普比率 0.44 vs 0.33

- **回测**: 见 `BACKTEST_LOG.md #14`



### ✅ V7-6 动态权重优化集成 (2026-04-07)

- **文件**: `main_v75_optimized.py`, `scripts/run_v75_backtest_with_optimized_weights.py`

- **效果**: 组合总收益 +17.23% (从+12.86%提升+4.37%)

- **每个指数独立优化权重**：

  - 深证成指: factor_score 85.46%, ml_return 3.79%, ml_signal 1.70%, factor_signal 9.05%

  - 创业板指: factor_score 83.13%, ml_return 11.43%, ml_signal 0.12%, factor_signal 5.32%

  - 上证综指: factor_score 84.58%, ml_return 0.95%, ml_signal 1.43%, factor_signal 13.05%

  - 沪深300: factor_score 84.17%, ml_return 7.92%, ml_signal 5.71%, factor_signal 2.20%

  - 科创50: factor_score 56.19%, ml_return 14.17%, ml_signal 15.20%, factor_signal 14.45%

- **回测验证**: 见 `BACKTEST_LOG.md #13`

- **关键发现**: 必须使用字符串信号（BUY/SELL/HOLD），不是数值（1/-1/0）



---



## 📋 第三部分：推荐实施路线



### 第一阶段：快速收益

1. **宏观因子** - 难度中高，效果直接

2. **跨指数特征** - 高价值，捕捉市场联动效应



### 第二阶段：模型增强

3. **多时间框架联动** - 过滤震荡市假信号

4. **信号融合规则优化** - 提高信号质量



### 第三阶段：高级功能

5. **Web Dashboard** - 用户体验提升



---



## 📋 第四部分：开发流程检查清单



每次优化时必须检查：



- [ ] 修改代码前读取本文件确认目标

- [ ] 修改代码实现功能

- [ ] **【必须】** 运行回测验证效果

- [ ] **【必须】** 确认收益率提升

- [ ] **【必须】** 更新本文件状态为"[x] 已实现"

- [ ] **【必须】** 更新`BACKTEST_LOG.md`记录回测结果

- [ ] **【必须】** 更新`AGENTS.md`记录项目状态

- [ ] Git提交并推送



---



## 📋 第五部分：历史记录



### 2026-04-11

- ✅ V8市场状态识别完成，6状态检测+动态参数调整

- ✅ 超额收益+22.60% (vs V7-7的+4.23%)，BUY/SELL比从0.46改善到1.03

- ✅ V7-7多指标共识投票完成，解决2023-2025信号稀疏问题



### 2026-04-05

- ✅ 完成项目文件整理

  - 测试文件移至 `tests/` 目录

  - 回测脚本移至 `scripts/` 目录

  - 说明文件合并精简

- ✅ 创建 `scripts/README.md` 和 `tests/README.md`

- 📊 TODO.md精简，只保留核心内容



### 2026-04-03

- ✅ V7-5自适应融合优化完成，组合总收益提升258.24%

- ✅ V7-4信号阈值优化完成，信号频率提升4300%



### 2026-04-01

- ✅ V7-2特征交叉优化完成

- ✅ V7版本仓位分配回测完成



### 2026-03-30

- ✅ V7-1模型持久化与增量预测完成

- ✅ V6激进仓位优化完成

- ✅ 特征重要性筛选完成



---



> 最后更新: 2026-04-19
> 
> 当前版本: V14 - 防鞭打增强优化，收益+80.39%(+9.77%)，回撤-21.21%(改善2.10pp)，超额+50.31%
> 
> 下一步: 跨指数特征 / Regime状态特征增强 / 多时间框架联动
