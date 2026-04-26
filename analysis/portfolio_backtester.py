"""
组合级回测引擎

基于多指数 fused_signal (V7-5) 信号，按 position_advisor 动态分配权重，
逐日仿真计算组合净值，生成综合报告与图表。

交易逻辑:
- T日信号 -> T+1日执行（延迟一天）
- 佣金: 万0.6 (单边)，仅在权重变化时收取
- 总仓位上限: 90%，剩余为现金

使用:
    from analysis.portfolio_backtester import PortfolioBacktester
    bt = PortfolioBacktester(start_date='20200101')
    results = bt.run()
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# 确保项目根目录在 path 中
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from entity import constant


class PortfolioBacktester:
    """
    组合级回测引擎

    功能:
    1. 加载 8 个指数数据，生成 fused_signal (V7-5)
    2. 基于 position_advisor 动态分配各指数权重
    3. 逐日仿真组合净值（含佣金、T+1 延迟）
    4. 计算组合绩效（收益、夏普、回撤、胜率等）
    5. 生成双 Y 轴图表（上证综指 vs 组合净值 + 买卖点）
    """

    SHANGHAI_CODE = '000001.SH'

    def __init__(self,
                 initial_capital: float = 100000,
                 commission_rate: float = 0.00006,
                 start_date: str = '20200101',
                 end_date: Optional[str] = None,
                 signal_column: str = 'fused_signal',
                 fallback_signal: str = 'final_signal',
                 position_window: int = 30,
                 total_position_cap: float = 1.0,
                 min_rebalance_threshold: float = 0.001,
                 chart_save_dir: str = 'records',
                 use_smart_position: bool = False,
                 cross_index_consensus_enabled: bool = True,
                 include_macro: bool = True,
                 exclude_codes: Optional[set] = None,
                 index_max_weight: Optional[Dict[str, float]] = None):
        """
        Args:
            initial_capital: 初始资金
            commission_rate: 单边佣金率 (万0.6 = 0.00006)
            start_date: 回测起始日期 (YYYYMMDD)
            end_date: 回测结束日期 (YYYYMMDD)，默认为当前日期
            signal_column: 主信号列名
            fallback_signal: 回退信号列名
            position_window: 滑动窗口天数 (用于计算信号分布)
            total_position_cap: 总仓位上限
            min_rebalance_threshold: 最小调仓阈值 (权重变化低于此值不调仓)
            chart_save_dir: 图表保存目录
            use_smart_position: 启用 V9 智能仓位管理
            cross_index_consensus_enabled: V12 启用跨指数趋势共识
            include_macro: V13 启用宏观因子
            exclude_codes: 从交易组合中排除的指数代码集合（但仍加载数据供跨指数共识）
            index_max_weight: 各指数最大仓位上限字典，如 {'000300.SH': 0.05}
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.start_date = start_date
        self.end_date = end_date
        self.signal_column = signal_column
        self.fallback_signal = fallback_signal
        self.position_window = position_window
        self.total_position_cap = total_position_cap
        self.min_rebalance_threshold = min_rebalance_threshold
        self.chart_save_dir = chart_save_dir
        self.use_smart_position = use_smart_position
        self.cross_index_consensus_enabled = cross_index_consensus_enabled
        self.include_macro = include_macro
        self.exclude_codes = exclude_codes or set()
        self.index_max_weight = index_max_weight or {}
        self._smart_managers = {}  # code -> SmartPositionManager
        # V10: 组合回撤熔断
        self._portfolio_peak: float = initial_capital
        self._drawdown_state: str = 'NORMAL'
        # V12: 跨指数共识EMA状态
        self._consensus_ema: float = 0.0

    def run(self) -> dict:
        """
        运行组合回测

        Returns:
            dict: 完整回测结果
        """
        print("=" * 70)
        print("  股票分析系统 - 组合回测引擎")
        print("=" * 70)
        print(f"  初始资金: {self.initial_capital:,.0f}")
        print(f"  佣金: 万{self.commission_rate * 10000:.1f} (单边)")
        print(f"  起始日期: {self.start_date}")
        print(f"  结束日期: {self.end_date or '至今'}")
        print(f"  信号策略: {self.signal_column}")
        print(f"  仓位上限: {self.total_position_cap * 100:.0f}%")
        if self.use_smart_position:
            print(f"  仓位模式: V9 智能仓位管理")
        if self.cross_index_consensus_enabled:
            print(f"  V16跨指数共识: 启用")
        print("=" * 70)

        # 1. 加载所有指数数据
        print("\n[1/5] 加载指数数据并生成信号...")
        index_data = self._load_all_indices()
        if len(index_data) < 2:
            print("[ERROR] 可用指数不足，无法进行组合回测")
            return {}

        # 初始化 V9 SmartPositionManager (每指数一个实例)
        if self.use_smart_position:
            from analysis.smart_position_manager import SmartPositionManager
            for code in index_data.keys():
                self._smart_managers[code] = SmartPositionManager()
            print(f"  V9 智能仓位管理: 已为 {len(self._smart_managers)} 个指数创建管理器")

        # 2. 日期对齐
        print(f"\n[2/5] 日期对齐... (共 {len(index_data)} 个指数)")
        common_dates, aligned_data = self._align_dates(index_data)
        print(f"  公共交易日: {len(common_dates)} 天")
        print(f"  日期范围: {common_dates[0].strftime('%Y-%m-%d')} ~ {common_dates[-1].strftime('%Y-%m-%d')}")

        if len(common_dates) < self.position_window + 10:
            print(f"[ERROR] 公共交易日不足 (需要至少 {self.position_window + 10} 天)")
            return {}

        # 确定实际使用的信号列
        actual_signal_col = self._resolve_signal_column(aligned_data)
        print(f"  使用信号列: {actual_signal_col}")

        # 3. 逐日仿真
        print(f"\n[3/5] 逐日仿真...")
        sim_result = self._simulate(aligned_data, common_dates, actual_signal_col)

        # 4. 计算绩效指标
        print(f"\n[4/5] 计算绩效指标...")
        metrics = self._calculate_metrics(sim_result, common_dates, aligned_data)

        # 5. 生成图表
        print(f"\n[5/5] 生成图表...")
        chart_path = self._generate_chart(
            common_dates, sim_result, metrics, aligned_data
        )
        metrics['chart_path'] = chart_path

        # 5b. 生成买卖详情图
        trade_detail_path = self._generate_trade_detail_chart(
            common_dates, sim_result, metrics, aligned_data
        )
        metrics['trade_detail_chart_path'] = trade_detail_path

        # 输出报告
        self._print_report(metrics)

        return metrics

    # ==================== 数据加载 ====================

    def _load_all_indices(self) -> Dict[str, pd.DataFrame]:
        """
        加载所有指数数据并生成信号

        关键设计: 信号生成与回测区间解耦
        - 始终使用全量历史数据生成信号 (从 HISTORY_START_DATE_MAP 开始)
        - 确保 ML 模型有充足训练数据，fused_score 归一化稳定
        - 回测区间仅控制交易仿真的起止时间 (在 _align_dates 中截取)
        """
        from analysis.index_analyzer import IndexAnalyzer

        index_data = {}
        codes = list(constant.TS_CODE_NAME_DICT.keys())

        for i, code in enumerate(codes):
            name = constant.TS_CODE_NAME_DICT.get(code, code)
            print(f"  [{i+1}/{len(codes)}] {name} ({code})...", end=" ", flush=True)

            try:
                # 始终使用全量历史数据生成信号，不受回测 start_date 限制
                full_start = constant.HISTORY_START_DATE_MAP.get(code, '20100101')
                analyzer = IndexAnalyzer(code, start_date=full_start, end_date=self.end_date,
                                         include_macro=self.include_macro)

                if len(analyzer.data) < 100:
                    print(f"数据不足 ({len(analyzer.data)} 行)，跳过")
                    continue

                analyzer.analyze(include_ml=True)

                # 尝试生成 fused_signal
                df = self._add_fused_signal(analyzer.data)

                # 截取回测区间: 信号已在全量数据上生成，现在只保留回测范围
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                bt_start = pd.to_datetime(self.start_date)
                df_backtest = df[df['trade_date'] >= bt_start].copy().reset_index(drop=True)

                if len(df_backtest) < 50:
                    print(f"回测区间数据不足 ({len(df_backtest)} 行)，跳过")
                    continue

                index_data[code] = df_backtest

                n_rows = len(df_backtest)
                n_full = len(df)
                sig_col = self.signal_column if self.signal_column in df_backtest.columns else self.fallback_signal
                if sig_col in df_backtest.columns:
                    n_buy = (df_backtest[sig_col] == 'BUY').sum()
                    n_sell = (df_backtest[sig_col] == 'SELL').sum()
                    print(f"OK (全量{n_full}行, 回测{n_rows}行, BUY={n_buy}, SELL={n_sell})")
                else:
                    print(f"OK (全量{n_full}行, 回测{n_rows}行, 信号列缺失)")

            except Exception as e:
                print(f"失败: {e}")

        return index_data

    def _add_fused_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        """尝试添加 fused_signal 列"""
        if self.signal_column == 'fused_signal' and 'fused_signal' not in df.columns:
            try:
                from analysis.adaptive_fusion_optimizer import MetaLearner
                meta = MetaLearner(max_trials=10)
                # 需要 factor_score, factor_signal, ml_predicted_return, ml_signal
                required = ['factor_score', 'factor_signal', 'ml_predicted_return', 'ml_signal']
                if all(c in df.columns for c in required):
                    df = meta.generate_fused_signal(df)
            except Exception:
                pass
        return df

    def _resolve_signal_column(self, aligned_data: Dict[str, pd.DataFrame]) -> str:
        """确定实际可用的信号列"""
        # 检查所有指数是否都有主信号列
        first_df = next(iter(aligned_data.values()))
        if self.signal_column in first_df.columns:
            return self.signal_column
        if self.fallback_signal in first_df.columns:
            print(f"  [WARNING] {self.signal_column} 不可用，回退到 {self.fallback_signal}")
            return self.fallback_signal
        # 最终回退
        for col in ['final_signal', 'factor_signal', 'ml_signal']:
            if col in first_df.columns:
                print(f"  [WARNING] 回退到 {col}")
                return col
        raise ValueError("没有可用的信号列")

    # ==================== 日期对齐 ====================

    def _align_dates(self, index_data: Dict[str, pd.DataFrame]) -> Tuple[list, Dict[str, pd.DataFrame]]:
        """
        将所有指数按公共交易日对齐

        Returns:
            (common_dates_sorted, aligned_data_dict)
        """
        # 取日期交集
        date_sets = []
        for code, df in index_data.items():
            dates = set(pd.to_datetime(df['trade_date']).dt.normalize())
            date_sets.append(dates)

        common_dates = set.intersection(*date_sets)
        common_dates = sorted(common_dates)

        if not common_dates:
            raise ValueError("没有公共交易日")

        # 过滤每个 DataFrame
        aligned = {}
        for code, df in index_data.items():
            df = df.copy()
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.normalize()
            df = df[df['trade_date'].isin(common_dates)].sort_values('trade_date').reset_index(drop=True)

            # 确保数值列
            for col in ['close', 'open', 'pct_chg']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            aligned[code] = df

        return common_dates, aligned

    # ==================== 权重计算 ====================

    def _compute_daily_weights(self,
                               aligned_data: Dict[str, pd.DataFrame],
                               day_idx: int,
                               signal_col: str) -> Dict[str, float]:
        """
        计算第 day_idx 天的目标仓位权重

        逻辑:
        1. 取滑动窗口内信号分布 -> position_advisor 计算建议仓位
        2. 按当日信号过滤 (SELL->0, HOLD->减半, BUY->保持)
        3. 归一化到 total_position_cap
        """
        codes = list(aligned_data.keys())
        n_codes = len(codes)

        # 预热期: 使用等权
        if day_idx < self.position_window:
            equal_weight = self.total_position_cap / n_codes
            weights = {}
            for code in codes:
                df = aligned_data[code]
                sig = df.iloc[day_idx].get(signal_col, 'HOLD')
                if sig == 'BUY':
                    weights[code] = equal_weight
                elif sig == 'HOLD':
                    weights[code] = equal_weight * 1.0
                else:
                    weights[code] = 0.0
            return self._normalize_weights(weights)

        # 正式期: 用 position_advisor 计算
        window_start = max(0, day_idx - self.position_window + 1)

        # 统计窗口内信号分布
        signals = {}
        for code in codes:
            df = aligned_data[code]
            window_signals = df[signal_col].iloc[window_start:day_idx + 1]
            total = len(window_signals)
            signals[code] = {
                'total_rows': total,
                'buy_signals': int((window_signals == 'BUY').sum()),
                'sell_signals': int((window_signals == 'SELL').sum()),
                'hold_signals': int((window_signals == 'HOLD').sum()),
            }

        # 调用 position_advisor
        try:
            from active_skills.stock_signal_generator.position_advisor import (
                calculate_position_score, get_position_advice, get_position_dict
            )
            df_score = calculate_position_score(signals)
            df_advice = get_position_advice(df_score)
            pos_dict = get_position_dict(df_advice)
        except Exception:
            # 如果 position_advisor 不可用，使用等权
            equal_weight = self.total_position_cap / n_codes
            return {code: equal_weight for code in codes}

        # 按当日信号过滤
        weights = {}
        for code in codes:
            df = aligned_data[code]
            current_signal = df.iloc[day_idx].get(signal_col, 'HOLD')

            advised_weight = pos_dict.get(code, {}).get('建议仓位', 0.5)

            if current_signal == 'BUY':
                weights[code] = advised_weight
            elif current_signal == 'HOLD':
                weights[code] = advised_weight * 1.0
            else:  # SELL
                weights[code] = 0.0

        return self._normalize_weights(weights)

    def _compute_smart_weights(self,
                               aligned_data: Dict[str, pd.DataFrame],
                               day_idx: int,
                               signal_col: str,
                               codes: list) -> Dict[str, float]:
        """
        V9: 使用 SmartPositionManager 计算每指数权重

        每个指数的 SmartPositionManager 独立 step(),
        输出 raw_position (0~1)。raw_position 直接作为权重基数，
        由 _normalize_weights 负责在总和超限时等比缩放。
        这样活跃指数能获得更多权重，非活跃指数不占用额度。
        """
        from analysis.smart_position_manager import _safe_float, _calc_confidence

        n_codes = len(codes)
        target_weights = {}

        for code in codes:
            df = aligned_data[code]
            row = df.iloc[day_idx]

            # 构造 row_data
            confidence = 0.5
            if 'fused_confidence' in df.columns:
                confidence = _safe_float(row.get('fused_confidence', 0.5), 0.5)
            elif 'fused_score' in df.columns:
                score = _safe_float(row.get('fused_score', 50.0), 50.0)
                confidence = abs(score - 50.0) / 50.0
            elif 'factor_score' in df.columns:
                score = _safe_float(row.get('factor_score', 50.0), 50.0)
                confidence = abs(score - 50.0) / 50.0

            # V10: 获取预计算的背离信号
            div_signal = None
            if hasattr(self, '_divergence_cache') and code in self._divergence_cache:
                div_series = self._divergence_cache[code]
                if day_idx < len(div_series):
                    div_signal = div_series.iloc[day_idx]

            row_data = {
                'fused_signal': row.get(signal_col, 'HOLD'),
                'fused_confidence': confidence,
                'rsi': _safe_float(row.get('rsi', 50.0), 50.0),
                'atr': _safe_float(row.get('atr', 0.0), 0.0),
                'close': _safe_float(row.get('close', 0.0), 0.0),
                'regime_label': row.get('regime_label', 'SIDEWAYS'),
                # V10 新增
                'vol': _safe_float(row.get('vol', 0.0), 0.0),
                'vol_ma_10': _safe_float(row.get('vol_ma_10', 0.0), 0.0),
                'divergence_signal': div_signal,
                # V11 新增
                'ma_50': _safe_float(row.get('ma_50', 0.0), 0.0),
            }

            mgr = self._smart_managers.get(code)
            if mgr is not None:
                raw_position = mgr.step(row_data)
            else:
                raw_position = 0.0

            # raw_position 直接作为权重，不除以 n_codes
            # 活跃指数获得更多资金，空仓指数不占用额度
            target_weights[code] = raw_position

        return self._normalize_weights(target_weights)

    def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """归一化权重到 total_position_cap"""
        total = sum(weights.values())
        if total <= 0:
            return {code: 0.0 for code in weights}
        if total <= self.total_position_cap:
            return weights
        factor = self.total_position_cap / total
        return {code: w * factor for code, w in weights.items()}

    # ==================== V10: 组合回撤熔断 ====================

    # 状态等级 (用于比较)
    _DRAWDOWN_RANKS = {'NORMAL': 0, 'CAUTION': 1, 'SEVERE': 2, 'EMERGENCY': 3}
    _DRAWDOWN_MULTIPLIER = {'NORMAL': 1.0, 'CAUTION': 0.7, 'SEVERE': 0.5, 'EMERGENCY': 0.0}

    def _apply_drawdown_circuit_breaker(self, portfolio_value: float,
                                        target_weights: Dict[str, float]) -> Dict[str, float]:
        """
        V10: 组合回撤三级熔断

        根据组合净值相对峰值的回撤幅度，动态缩减所有权重。
        使用滞后恢复阈值防止在边界处频繁切换。

        熔断级别:
            NORMAL   -> CAUTION  : 回撤 < -20%  (权重 * 0.7)
            CAUTION  -> SEVERE   : 回撤 < -30%  (权重 * 0.5)
            SEVERE   -> EMERGENCY: 回撤 < -40%  (全部清仓)

        恢复条件 (滞后):
            EMERGENCY -> SEVERE  : 回撤 > -25%
            SEVERE    -> CAUTION : 回撤 > -15%
            CAUTION   -> NORMAL  : 回撤 > -8%
        """
        self._portfolio_peak = max(self._portfolio_peak, portfolio_value)
        if self._portfolio_peak <= 0:
            return target_weights

        drawdown = (portfolio_value - self._portfolio_peak) / self._portfolio_peak

        prev_state = self._drawdown_state
        curr_rank = self._DRAWDOWN_RANKS.get(self._drawdown_state, 0)

        # 状态升级 (更严格): 只能升级不能跳过
        if drawdown < -0.40 and curr_rank < 3:
            self._drawdown_state = 'EMERGENCY'
        elif drawdown < -0.30 and curr_rank < 2:
            self._drawdown_state = 'SEVERE'
        elif drawdown < -0.20 and curr_rank < 1:
            self._drawdown_state = 'CAUTION'

        # 状态降级 (恢复): 每次只降一级，且使用更宽松的阈值
        if self._drawdown_state == 'EMERGENCY' and drawdown > -0.25:
            self._drawdown_state = 'SEVERE'
        elif self._drawdown_state == 'SEVERE' and drawdown > -0.15:
            self._drawdown_state = 'CAUTION'
        elif self._drawdown_state == 'CAUTION' and drawdown > -0.08:
            self._drawdown_state = 'NORMAL'

        multiplier = self._DRAWDOWN_MULTIPLIER.get(self._drawdown_state, 1.0)

        if multiplier >= 1.0:
            return target_weights

        return {code: w * multiplier for code, w in target_weights.items()}

    # ==================== V12: 跨指数趋势共识 ====================

    # 缩放系数表: (平滑后n_below_ma50阈值, 缩放系数) - R4柔化版
    _CONSENSUS_SCALING = [
        (7, 0.50),
        (6, 0.70),
        (5, 0.85),
    ]

    def _apply_cross_index_consensus(self,
                                     aligned_data: Dict[str, pd.DataFrame],
                                     day_idx: int,
                                     target_weights: Dict[str, float]) -> Dict[str, float]:
        """
        V12: 跨指数趋势共识过滤

        当多数指数同时跌破MA50时, 缩减整个组合仓位。
        使用非对称EMA平滑: 快速进入保护, 慢速恢复。

        与SmartPositionManager Phase 7互补:
        - Phase 7: 单指数close < MA50时限制该指数仓位
        - L1: 多数指数同时走弱时缩减整个组合

        Args:
            aligned_data: 对齐后的各指数数据
            day_idx: 当前日序号
            target_weights: 当前目标权重

        Returns:
            缩放后的目标权重
        """
        if not self.cross_index_consensus_enabled:
            return target_weights

        codes = list(aligned_data.keys())

        # 统计低于MA50/MA20的指数数
        n_below_ma50 = 0
        n_below_ma20 = 0
        n_valid = 0

        for code in codes:
            df = aligned_data[code]
            row = df.iloc[day_idx]

            close = pd.to_numeric(row.get('close', None), errors='coerce')
            ma50 = pd.to_numeric(row.get('ma_50', None), errors='coerce')
            ma20 = pd.to_numeric(row.get('ma_20', None), errors='coerce')

            if pd.notna(close) and pd.notna(ma50) and ma50 > 0:
                n_valid += 1
                if close < ma50:
                    n_below_ma50 += 1

            if pd.notna(close) and pd.notna(ma20) and ma20 > 0:
                if close < ma20:
                    n_below_ma20 += 1

        # 有效指数不足时跳过
        if n_valid < 6:
            return target_weights

        # 非对称EMA平滑 - R4: 放慢进入速度, 避免短期修正误触发
        if n_below_ma50 > self._consensus_ema:
            # 进入保护: 中速响应 (~7日半衰期)
            alpha = 0.2
        else:
            # 恢复: 慢速退出
            alpha = 0.1
        self._consensus_ema = alpha * n_below_ma50 + (1 - alpha) * self._consensus_ema

        # 根据平滑后的计数确定缩放系数
        scaling = 1.0
        for threshold, scale in self._CONSENSUS_SCALING:
            if self._consensus_ema >= threshold:
                scaling = scale
                break

        if scaling >= 1.0:
            return target_weights

        return {code: w * scaling for code, w in target_weights.items()}

    # ==================== 逐日仿真 ====================

    def _simulate(self,
                  aligned_data: Dict[str, pd.DataFrame],
                  common_dates: list,
                  signal_col: str) -> dict:
        """
        逐日仿真组合

        Returns:
            dict: {
                'portfolio_values': list,
                'daily_returns': list,
                'benchmark_values': list,
                'trade_events': list,
                'total_commission': float,
                'index_weights_history': list,
                'index_contributions': dict
            }
        """
        n_days = len(common_dates)
        codes = list(aligned_data.keys())
        # 排除的指数代码不参与交易，但仍参与跨指数共识
        tradeable_codes = [c for c in codes if c not in self.exclude_codes]
        n_tradeable = len(tradeable_codes)

        portfolio_value = self.initial_capital
        index_weights = {code: 0.0 for code in tradeable_codes}
        prev_target_weights = None

        # V10: 重置熔断状态
        self._portfolio_peak = self.initial_capital
        self._drawdown_state = 'NORMAL'

        # V12: 重置跨指数共识EMA
        self._consensus_ema = 0.0

        # V10: 预计算背离信号 (每个指数独立)
        self._divergence_cache = {}
        if self.use_smart_position:
            from analysis.smart_position_manager import SmartPositionManager
            for code in codes:
                self._divergence_cache[code] = SmartPositionManager._detect_divergences(
                    aligned_data[code])

        portfolio_values = [portfolio_value]
        daily_returns_list = [0.0]
        trade_events = []
        total_commission = 0.0
        index_weights_history = []

        # 跟踪每指数贡献
        index_cumulative_contribution = {code: 0.0 for code in tradeable_codes}
        index_avg_weight_sum = {code: 0.0 for code in tradeable_codes}

        # 基准: 等权买入持有 (仅可交易指数)
        benchmark_value = self.initial_capital
        benchmark_weight = 1.0 / n_tradeable if n_tradeable > 0 else 0.0
        benchmark_values = [benchmark_value]

        for t in range(n_days):
            # 计算今日目标权重 (仅可交易指数)
            if self.use_smart_position and self._smart_managers:
                target_weights = self._compute_smart_weights(
                    aligned_data, t, signal_col, codes)
            else:
                target_weights = self._compute_daily_weights(aligned_data, t, signal_col)

            # 排除指数权重强制归零（释放的权重变为现金，降低风险敞口）
            for code in self.exclude_codes:
                target_weights.pop(code, None)

            # 应用单指数最大仓位上限
            for code in list(target_weights.keys()):
                max_w = self.index_max_weight.get(code, 1.0)
                if target_weights[code] > max_w:
                    target_weights[code] = max_w

            # 排除+限仓释放的权重重新分配，保持总仓位水平
            remaining_sum = sum(target_weights.values())
            if remaining_sum > 0 and remaining_sum < self.total_position_cap * 0.95:
                scale = self.total_position_cap / remaining_sum
                target_weights = {c: w * scale for c, w in target_weights.items()}

            # V12: 跨指数趋势共识过滤 (使用全部代码，含排除指数)
            if self.cross_index_consensus_enabled:
                target_weights = self._apply_cross_index_consensus(
                    aligned_data, t, target_weights)

            # T+1 延迟: 执行昨日的目标权重
            if t > 0 and prev_target_weights is not None:
                # 计算调仓佣金
                day_commission = 0.0
                for code in tradeable_codes:
                    weight_change = abs(prev_target_weights.get(code, 0.0) - index_weights.get(code, 0.0))
                    if weight_change > self.min_rebalance_threshold:
                        cost = weight_change * portfolio_value * self.commission_rate
                        day_commission += cost
                total_commission += day_commission
                portfolio_value -= day_commission

                # 更新权重
                index_weights = dict(prev_target_weights)

            # 计算今日组合收益
            daily_return = 0.0
            for code in tradeable_codes:
                w = index_weights.get(code, 0.0)
                if w > 0:
                    df = aligned_data[code]
                    pct = df.iloc[t].get('pct_chg', 0)
                    if pd.notna(pct):
                        pct = float(pct) / 100.0
                        ret_contribution = w * pct
                        daily_return += ret_contribution
                        index_cumulative_contribution[code] += ret_contribution

            if t > 0:
                portfolio_value *= (1 + daily_return)
                portfolio_values.append(portfolio_value)
                daily_returns_list.append(daily_return)

                # 基准收益 (仅可交易指数)
                bm_return = 0.0
                for code in tradeable_codes:
                    df = aligned_data[code]
                    pct = df.iloc[t].get('pct_chg', 0)
                    if pd.notna(pct):
                        bm_return += float(pct) / 100.0 * benchmark_weight
                benchmark_value *= (1 + bm_return)
                benchmark_values.append(benchmark_value)

            # 记录权重
            index_weights_history.append(dict(index_weights))
            for code in tradeable_codes:
                index_avg_weight_sum[code] += index_weights.get(code, 0.0)

            # 记录买卖事件
            if prev_target_weights is not None:
                prev_total = sum(prev_target_weights.values())
                curr_total = sum(target_weights.values())
                net_change = curr_total - prev_total
                if net_change > 0.03:
                    trade_events.append({
                        'date': common_dates[t],
                        'type': 'BUY',
                        'net_change': net_change,
                        'day_idx': t,
                    })
                elif net_change < -0.03:
                    trade_events.append({
                        'date': common_dates[t],
                        'type': 'SELL',
                        'net_change': net_change,
                        'day_idx': t,
                    })

            prev_target_weights = target_weights

        # 计算平均权重
        index_avg_weights = {
            code: index_avg_weight_sum[code] / n_days for code in tradeable_codes
        }

        return {
            'portfolio_values': portfolio_values,
            'daily_returns': daily_returns_list,
            'benchmark_values': benchmark_values,
            'trade_events': trade_events,
            'total_commission': total_commission,
            'index_weights_history': index_weights_history,
            'index_avg_weights': index_avg_weights,
            'index_cumulative_contribution': index_cumulative_contribution,
        }

    # ==================== 绩效计算 ====================

    def _calculate_metrics(self, sim_result: dict, common_dates: list,
                           aligned_data: Dict[str, pd.DataFrame]) -> dict:
        """计算组合绩效指标"""
        pv = np.array(sim_result['portfolio_values'])
        bv = np.array(sim_result['benchmark_values'])
        dr = np.array(sim_result['daily_returns'])

        trading_days = len(pv)
        final_value = pv[-1]
        bm_final = bv[-1]

        # 总收益
        total_return = (final_value - self.initial_capital) / self.initial_capital
        bm_total_return = (bm_final - self.initial_capital) / self.initial_capital

        # 年化收益
        if trading_days > 1:
            ann_return = (1 + total_return) ** (252 / trading_days) - 1
            bm_ann = (1 + bm_total_return) ** (252 / trading_days) - 1
        else:
            ann_return = 0.0
            bm_ann = 0.0

        # 最大回撤
        max_dd = self._max_drawdown(pv)
        bm_max_dd = self._max_drawdown(bv)

        # 夏普比率
        sharpe = self._sharpe_ratio(dr)
        bm_dr = np.diff(bv) / bv[:-1]
        bm_dr = np.insert(bm_dr, 0, 0.0)
        bm_sharpe = self._sharpe_ratio(bm_dr)

        # 月度胜率
        monthly_wr, months_positive, months_total = self._monthly_win_rate(
            common_dates, sim_result['daily_returns']
        )

        # 每指数贡献
        index_stats = {}
        codes = list(aligned_data.keys())
        for code in codes:
            name = constant.TS_CODE_NAME_DICT.get(code, code)
            df = aligned_data[code]
            sig_col = self.signal_column if self.signal_column in df.columns else self.fallback_signal
            n_buy = 0
            n_sell = 0
            n_hold = 0
            if sig_col in df.columns:
                n_buy = int((df[sig_col] == 'BUY').sum())
                n_sell = int((df[sig_col] == 'SELL').sum())
                n_hold = int((df[sig_col] == 'HOLD').sum())
            index_stats[code] = {
                'name': name,
                'avg_weight': sim_result['index_avg_weights'].get(code, 0),
                'contribution': sim_result['index_cumulative_contribution'].get(code, 0),
                'buy_count': n_buy,
                'sell_count': n_sell,
                'hold_count': n_hold,
            }

        # 交易统计
        buy_events = [e for e in sim_result['trade_events'] if e['type'] == 'BUY']
        sell_events = [e for e in sim_result['trade_events'] if e['type'] == 'SELL']

        commission_ratio = sim_result['total_commission'] / self.initial_capital * 100

        return {
            'total_return': round(total_return * 100, 2),
            'annualized_return': round(ann_return * 100, 2),
            'max_drawdown': round(max_dd * 100, 2),
            'sharpe_ratio': round(sharpe, 2),
            'monthly_win_rate': round(monthly_wr * 100, 1),
            'months_positive': months_positive,
            'months_total': months_total,
            'final_value': round(final_value, 2),
            'benchmark_total_return': round(bm_total_return * 100, 2),
            'benchmark_annualized': round(bm_ann * 100, 2),
            'benchmark_max_drawdown': round(bm_max_dd * 100, 2),
            'benchmark_sharpe': round(bm_sharpe, 2),
            'excess_return': round((total_return - bm_total_return) * 100, 2),
            'trading_days': trading_days,
            'total_commission': round(sim_result['total_commission'], 2),
            'commission_ratio': round(commission_ratio, 2),
            'buy_events_count': len(buy_events),
            'sell_events_count': len(sell_events),
            'index_stats': index_stats,
            'start_date': common_dates[0].strftime('%Y-%m-%d'),
            'end_date': common_dates[-1].strftime('%Y-%m-%d'),
            'portfolio_values': sim_result['portfolio_values'],
            'benchmark_values': sim_result['benchmark_values'],
            'trade_events': sim_result['trade_events'],
        }

    @staticmethod
    def _max_drawdown(values) -> float:
        """计算最大回撤"""
        values = np.array(values)
        peak = np.maximum.accumulate(values)
        drawdown = (values - peak) / peak
        return abs(drawdown.min()) if len(drawdown) > 0 else 0.0

    @staticmethod
    def _sharpe_ratio(daily_returns, risk_free_rate: float = 0.02) -> float:
        """计算夏普比率"""
        dr = np.array(daily_returns)
        if len(dr) < 2 or dr.std() == 0:
            return 0.0
        excess = dr.mean() - risk_free_rate / 252
        return float(excess / dr.std() * np.sqrt(252))

    @staticmethod
    def _monthly_win_rate(dates: list, daily_returns: list) -> Tuple[float, int, int]:
        """
        计算月度胜率

        Returns:
            (win_rate, months_positive, months_total)
        """
        if len(dates) < 2:
            return 0.0, 0, 0

        # 按月分组
        df = pd.DataFrame({'date': dates[:len(daily_returns)], 'return': daily_returns})
        df['month'] = pd.to_datetime(df['date']).dt.to_period('M')
        monthly = df.groupby('month')['return'].sum()

        months_total = len(monthly)
        months_positive = int((monthly > 0).sum())
        win_rate = months_positive / months_total if months_total > 0 else 0.0

        return win_rate, months_positive, months_total

    # ==================== 图表生成 ====================

    def _generate_chart(self,
                        common_dates: list,
                        sim_result: dict,
                        metrics: dict,
                        aligned_data: Dict[str, pd.DataFrame]) -> str:
        """
        生成双 Y 轴图表: 上证综指走势 vs 组合净值 + 买卖点

        Returns:
            str: 图表保存路径
        """
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
        except ImportError:
            print("  [WARNING] matplotlib 不可用，跳过图表生成")
            return ''

        # 中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        fig, ax1 = plt.subplots(figsize=(16, 10))

        portfolio_values = sim_result['portfolio_values']
        benchmark_values = sim_result['benchmark_values']
        trade_events = sim_result['trade_events']

        # 日期处理
        plot_dates = [pd.to_datetime(d) for d in common_dates[:len(portfolio_values)]]

        # 左 Y 轴: 上证综指
        if self.SHANGHAI_CODE in aligned_data:
            sh_df = aligned_data[self.SHANGHAI_CODE]
            sh_close = sh_df['close'].values[:len(plot_dates)]
            ax1.plot(plot_dates, sh_close, color='#AAAAAA', linewidth=1.2,
                     linestyle='--', label='上证综指', alpha=0.7)
            ax1.set_ylabel('上证综指', color='#666666', fontsize=12)
            ax1.tick_params(axis='y', labelcolor='#666666')

        ax1.set_xlabel('日期', fontsize=12)

        # 右 Y 轴: 组合净值 + 基准
        ax2 = ax1.twinx()
        ax2.plot(plot_dates, portfolio_values, color='#E74C3C', linewidth=2.0,
                 label='组合净值', zorder=5)
        ax2.plot(plot_dates, benchmark_values, color='#3498DB', linewidth=1.5,
                 linestyle='--', label='等权买入持有', alpha=0.8, zorder=4)
        ax2.set_ylabel('组合净值 (元)', color='#333333', fontsize=12)
        ax2.tick_params(axis='y', labelcolor='#333333')

        # 买卖点标注
        for event in trade_events:
            idx = event['day_idx']
            if idx < len(portfolio_values):
                event_date = plot_dates[idx]
                event_value = portfolio_values[idx]
                if event['type'] == 'BUY':
                    ax2.scatter(event_date, event_value, marker='^', color='#E74C3C',
                                s=60, zorder=10, edgecolors='darkred', linewidth=0.5)
                else:
                    ax2.scatter(event_date, event_value, marker='v', color='#27AE60',
                                s=60, zorder=10, edgecolors='darkgreen', linewidth=0.5)

        # 标题
        title = (f"组合回测: {metrics['start_date']} ~ {metrics['end_date']}  "
                 f"(佣金 万{self.commission_rate * 10000:.1f})")
        ax1.set_title(title, fontsize=14, fontweight='bold', pad=15)

        # 绩效信息框
        info_text = (
            f"总收益: {metrics['total_return']:+.2f}%\n"
            f"年化收益: {metrics['annualized_return']:+.2f}%\n"
            f"夏普比率: {metrics['sharpe_ratio']:.2f}\n"
            f"最大回撤: -{metrics['max_drawdown']:.2f}%\n"
            f"月度胜率: {metrics['monthly_win_rate']:.1f}%\n"
            f"超额收益: {metrics['excess_return']:+.2f}%\n"
            f"(vs 等权买入持有)"
        )
        props = dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.85)
        ax2.text(0.02, 0.97, info_text, transform=ax2.transAxes, fontsize=10,
                 verticalalignment='top', bbox=props, family='monospace')

        # 图例 - 合并两个轴
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()

        # 添加买卖标记到图例
        buy_marker = plt.Line2D([0], [0], marker='^', color='w', markerfacecolor='#E74C3C',
                                markersize=8, label='组合加仓')
        sell_marker = plt.Line2D([0], [0], marker='v', color='w', markerfacecolor='#27AE60',
                                 markersize=8, label='组合减仓')
        all_handles = lines1 + lines2 + [buy_marker, sell_marker]
        all_labels = labels1 + labels2 + ['组合加仓', '组合减仓']
        ax2.legend(all_handles, all_labels, loc='upper right', fontsize=9)

        # X 轴日期格式
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

        ax1.grid(True, alpha=0.3)
        fig.tight_layout()

        # 保存
        os.makedirs(self.chart_save_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d')
        filepath = os.path.join(self.chart_save_dir, f'portfolio_backtest_{timestamp}.png')
        fig.savefig(filepath, dpi=200, bbox_inches='tight')
        plt.close(fig)
        print(f"  图表已保存: {filepath}")
        return filepath

    def _generate_trade_detail_chart(self,
                                     common_dates: list,
                                     sim_result: dict,
                                     metrics: dict,
                                     aligned_data: Dict[str, pd.DataFrame]) -> str:
        """
        生成每指数买卖详情图: 8个子图, 每个显示收盘价+仓位权重+买卖标记

        Returns:
            str: 图表保存路径
        """
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from matplotlib.patches import Patch
            from matplotlib.lines import Line2D
        except ImportError:
            print("  [WARNING] matplotlib 不可用，跳过买卖详情图")
            return ''

        from entity import constant

        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        index_weights_history = sim_result.get('index_weights_history', [])
        if not index_weights_history:
            print("  [WARNING] 无权重历史数据，跳过买卖详情图")
            return ''

        # 获取所有指数代码 (按 constant 中的顺序)
        codes = [c for c in constant.TS_CODE_LIST if c in aligned_data]
        n_codes = len(codes)
        if n_codes == 0:
            return ''

        # 布局: 4行2列
        n_rows = (n_codes + 1) // 2
        fig, axes = plt.subplots(n_rows, 2, figsize=(20, n_rows * 3.5), squeeze=False)

        portfolio_values = sim_result['portfolio_values']
        n_days = min(len(common_dates), len(portfolio_values), len(index_weights_history))
        plot_dates = [pd.to_datetime(d) for d in common_dates[:n_days]]

        for i, code in enumerate(codes):
            row, col = i // 2, i % 2
            ax1 = axes[row][col]
            name = constant.TS_CODE_NAME_DICT.get(code, code)

            df = aligned_data[code]
            close_prices = df['close'].values[:n_days]

            # 提取该指数每日权重
            weights = []
            for day_idx in range(n_days):
                w = index_weights_history[day_idx].get(code, 0.0)
                weights.append(w)
            weights = np.array(weights)

            # ---- 左 Y 轴: 收盘价 ----
            ax1.plot(plot_dates, close_prices, color='#2C3E50', linewidth=1.0,
                     label='收盘价', zorder=3)
            ax1.set_ylabel('价格', fontsize=8, color='#2C3E50')
            ax1.tick_params(axis='y', labelsize=7, labelcolor='#2C3E50')

            # ---- 右 Y 轴: 仓位权重 (填充面积) ----
            ax2 = ax1.twinx()
            ax2.fill_between(plot_dates, 0, weights, alpha=0.25, color='#3498DB',
                             label='仓位', zorder=1)
            ax2.set_ylim(0, max(1.0, weights.max() * 1.2) if weights.max() > 0 else 1.0)
            ax2.set_ylabel('仓位', fontsize=8, color='#3498DB')
            ax2.tick_params(axis='y', labelsize=7, labelcolor='#3498DB')

            # ---- 检测买卖点 ----
            buy_dates, buy_prices = [], []
            sell_dates, sell_prices = [], []
            threshold = 0.02  # 权重变化阈值 2%

            for j in range(1, n_days):
                delta = weights[j] - weights[j - 1]
                if delta > threshold:
                    buy_dates.append(plot_dates[j])
                    buy_prices.append(close_prices[j])
                elif delta < -threshold:
                    sell_dates.append(plot_dates[j])
                    sell_prices.append(close_prices[j])

            if buy_dates:
                ax1.scatter(buy_dates, buy_prices, marker='^', color='#E74C3C',
                            s=30, zorder=10, edgecolors='darkred', linewidth=0.5,
                            label=f'买入({len(buy_dates)})')
            if sell_dates:
                ax1.scatter(sell_dates, sell_prices, marker='v', color='#27AE60',
                            s=30, zorder=10, edgecolors='darkgreen', linewidth=0.5,
                            label=f'卖出({len(sell_dates)})')

            # ---- 标题和图例 ----
            avg_w = weights.mean() * 100
            # 计算该指数的收益贡献
            contrib = sim_result.get('index_cumulative_contribution', {}).get(code, 0.0)
            ax1.set_title(f'{name}  (平均仓位 {avg_w:.1f}%, 贡献 {contrib:+.1f}%)',
                          fontsize=9, fontweight='bold')

            # 合并图例
            h1, l1 = ax1.get_legend_handles_labels()
            h2, l2 = ax2.get_legend_handles_labels()
            ax1.legend(h1 + h2, l1 + l2, loc='upper left', fontsize=6,
                       framealpha=0.7, ncol=2)

            # X 轴
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%y-%m'))
            ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha='right', fontsize=6)
            ax1.grid(True, alpha=0.2)

        # 隐藏多余的子图
        for i in range(n_codes, n_rows * 2):
            row, col = i // 2, i % 2
            axes[row][col].set_visible(False)

        # 总标题
        title = (f"各指数买卖详情: {metrics['start_date']} ~ {metrics['end_date']}  "
                 f"组合收益 {metrics['total_return']:+.2f}%  "
                 f"最大回撤 -{metrics['max_drawdown']:.2f}%  "
                 f"夏普 {metrics['sharpe_ratio']:.2f}")
        fig.suptitle(title, fontsize=13, fontweight='bold', y=1.01)
        fig.tight_layout()

        # 保存
        os.makedirs(self.chart_save_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d')
        filepath = os.path.join(self.chart_save_dir, f'portfolio_trade_detail_{timestamp}.png')
        fig.savefig(filepath, dpi=200, bbox_inches='tight')
        plt.close(fig)
        print(f"  买卖详情图已保存: {filepath}")
        return filepath

    # ==================== 报告输出 ====================

    def _print_report(self, metrics: dict):
        """控制台输出组合回测报告"""
        print(f"\n{'=' * 70}")
        print("  股票分析系统 - 组合回测报告")
        print(f"  回测期间: {metrics['start_date']} ~ {metrics['end_date']} "
              f"(共 {metrics['trading_days']} 交易日)")
        print(f"  初始资金: {self.initial_capital:,.0f} | "
              f"佣金: 万{self.commission_rate * 10000:.1f} | T+1执行")
        print(f"{'=' * 70}")

        print(f"\n  [组合绩效]")
        print(f"    总收益率:       {metrics['total_return']:+.2f}%")
        print(f"    年化收益率:     {metrics['annualized_return']:+.2f}%")
        print(f"    最大回撤:       -{metrics['max_drawdown']:.2f}%")
        print(f"    夏普比率:       {metrics['sharpe_ratio']:.2f}")
        print(f"    月度胜率:       {metrics['monthly_win_rate']:.1f}% "
              f"({metrics['months_positive']}/{metrics['months_total']} 个月)")
        print(f"    期末净值:       {metrics['final_value']:,.2f}")

        print(f"\n  [基准对比 (等权买入持有)]")
        print(f"    基准收益:       {metrics['benchmark_total_return']:+.2f}%")
        print(f"    超额收益:       {metrics['excess_return']:+.2f}%")
        print(f"    基准最大回撤:   -{metrics['benchmark_max_drawdown']:.2f}%")
        print(f"    基准夏普比率:   {metrics['benchmark_sharpe']:.2f}")

        # 各指数贡献
        index_stats = metrics.get('index_stats', {})
        if index_stats:
            print(f"\n  [各指数贡献]")
            header = f"    {'指数':<10} {'平均权重':>8} {'累计贡献':>10} {'BUY':>5} {'SELL':>5} {'HOLD':>5}"
            print(header)
            print(f"    {'─' * 52}")
            for code, stats in index_stats.items():
                name = stats['name']
                avg_w = stats['avg_weight'] * 100
                contrib = stats['contribution'] * 100
                print(f"    {name:<10} {avg_w:>7.1f}% {contrib:>+9.2f}% "
                      f"{stats['buy_count']:>5} {stats['sell_count']:>5} {stats['hold_count']:>5}")

        print(f"\n  [交易统计]")
        print(f"    组合加仓次数:   {metrics['buy_events_count']} 次")
        print(f"    组合减仓次数:   {metrics['sell_events_count']} 次")
        print(f"    总手续费:       {metrics['total_commission']:,.2f} 元")
        print(f"    手续费占比:     {metrics['commission_ratio']:.2f}%")

        chart_path = metrics.get('chart_path', '')
        if chart_path:
            print(f"\n  [图表已保存]")
            print(f"    {chart_path}")

        print(f"\n{'=' * 70}")
