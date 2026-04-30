"""
V13 市场状态识别模块

通过趋势、波动率、情绪、宏观四个维度识别市场所处的制度(Regime)，
并据此为下游模块提供动态参数调整依据。

6种市场状态:
- BULL_TREND: 强趋势上行
- BULL_LATE:  牛市末期(高估值+高波动)
- BEAR_TREND: 强趋势下行
- BEAR_LATE:  熊市末期(低估值+缩量)
- SIDEWAYS:   震荡市
- HIGH_VOL:   高波动无方向

维度:
1. 趋势维度 (0-100): MA50斜率 + Price/MA50位置 + ADX方向强度
2. 波动维度 (0-100): ATR百分位 + BB宽度百分位 + 实际波动率比
3. 情绪维度 (0-100): PE百分位 + 成交量/均线比 + RSI极端区间
4. 宏观维度 (0-100): 利率 + 北向资金 + 融资融券 + 汇率 [V13新增]

设计原则:
1. 仅使用当前及之前数据(无未来泄露)
2. 50日滚动窗口 + 5日众数平滑防抖
3. 施密特触发器防止状态边界跳变
4. 向后兼容: 数据不足时默认 SIDEWAYS
5. V13: 宏观恶化可加速进入BEAR_TREND, 宏观转好可辅助识别BEAR_LATE底部
"""

import json
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd


# 市场状态常量
BULL_TREND = 'BULL_TREND'
BULL_LATE = 'BULL_LATE'
BEAR_TREND = 'BEAR_TREND'
BEAR_LATE = 'BEAR_LATE'
SIDEWAYS = 'SIDEWAYS'
HIGH_VOL = 'HIGH_VOL'

# 各状态对应的共识投票阈值
CONSENSUS_THRESHOLDS = {
    BULL_TREND: {'bull_thresh': 3, 'bear_thresh': -3},
    BULL_LATE:  {'bull_thresh': 4, 'bear_thresh': -2},
    BEAR_TREND: {'bull_thresh': 4, 'bear_thresh': -2},
    BEAR_LATE:  {'bull_thresh': 3, 'bear_thresh': -3},
    SIDEWAYS:   {'bull_thresh': 4, 'bear_thresh': -2},   # V12: -3 -> -2, 震荡市更易产生SELL
    HIGH_VOL:   {'bull_thresh': 4, 'bear_thresh': -2},   # V12: -3 -> -2, 高波动更易产生SELL
}

# 各状态对应的多因子权重
FACTOR_WEIGHTS_BY_REGIME = {
    BULL_TREND: {'trend': 0.40, 'momentum': 0.30, 'volume': 0.10, 'valuation': 0.10, 'volatility': 0.10},
    BULL_LATE:  {'trend': 0.20, 'momentum': 0.15, 'volume': 0.15, 'valuation': 0.30, 'volatility': 0.20},
    BEAR_TREND: {'trend': 0.25, 'momentum': 0.15, 'volume': 0.20, 'valuation': 0.25, 'volatility': 0.15},
    BEAR_LATE:  {'trend': 0.25, 'momentum': 0.20, 'volume': 0.15, 'valuation': 0.30, 'volatility': 0.10},
    SIDEWAYS:   {'trend': 0.25, 'momentum': 0.25, 'volume': 0.20, 'valuation': 0.20, 'volatility': 0.10},
    HIGH_VOL:   {'trend': 0.20, 'momentum': 0.15, 'volume': 0.15, 'valuation': 0.20, 'volatility': 0.30},
}


class MarketRegimeDetector:
    """
    市场状态识别器

    四维度评分:
    - 趋势维度 (0-100): MA50斜率 + Price/MA50位置 + ADX方向强度
    - 波动维度 (0-100): ATR百分位 + BB宽度百分位 + 实际波动率比
    - 情绪维度 (0-100): PE百分位 + 成交量/均线比 + RSI极端区间
    - 宏观维度 (0-100): 利率 + 北向资金 + 融资融券 + 汇率 [V13新增]

    使用示例:
        detector = MarketRegimeDetector()
        df = detector.detect(df)
        # df 新增列: regime_label, regime_score,
        #            regime_trend_score, regime_vol_score, regime_sent_score,
        #            regime_macro_score
    """

    # 分类阈值
    THRESHOLDS = {
        BULL_TREND: {'trend_min': 65, 'vol_max': 65, 'sent_max': 75},
        BULL_LATE:  {'trend_min': 55, 'sent_min': 75},
        BEAR_TREND: {'trend_max': 40, 'vol_max': 70},  # V12: 35->40, 65->70, 捕获缓慢下跌
        BEAR_LATE:  {'trend_max': 45, 'sent_max': 25},
        HIGH_VOL:   {'vol_min': 75, 'trend_range': 15},
    }

    # 施密特触发器边距
    HYSTERESIS = 5

    def __init__(self,
                 lookback_window: int = 50,
                 smooth_window: int = 5,
                 min_persist_days: int = 3,
                 momentum_lookback: int = 10,
                 momentum_bear_threshold: float = -25):
        """
        Args:
            lookback_window: 滚动窗口天数 (用于百分位计算)
            smooth_window: 平滑窗口天数 (众数平滑防抖)
            min_persist_days: 新状态最少持续天数才生效
            momentum_lookback: V12 趋势动量回看天数
            momentum_bear_threshold: V12 趋势动量偏置阈值 (负值, 越小越严格)
        """
        self.lookback_window = lookback_window
        self.smooth_window = smooth_window
        self.min_persist_days = min_persist_days
        self.momentum_lookback = momentum_lookback
        self.momentum_bear_threshold = momentum_bear_threshold

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        检测市场状态

        Args:
            df: 包含技术指标的 DataFrame (需含 close, ma_50, adx, plus_di, minus_di,
                atr, bb_high, bb_low, bb_mid, rsi, vol, vol_ma_10, pct_chg,
                percentile_ranks 等列，可选宏观列 macro_score 等)

        Returns:
            pd.DataFrame: 新增 regime_label, regime_score,
                          regime_trend_score, regime_vol_score, regime_sent_score,
                          regime_macro_score 列
        """
        result = df.copy()

        # 确保数值类型
        numeric_cols = [
            'close', 'ma_50', 'adx', 'plus_di', 'minus_di',
            'atr', 'bb_high', 'bb_low', 'bb_mid', 'rsi',
            'vol', 'vol_ma_10', 'pct_chg'
        ]
        for col in numeric_cols:
            if col in result.columns:
                result[col] = pd.to_numeric(result[col], errors='coerce')

        # 计算三维度评分
        trend_scores = self._calc_trend_scores(result)
        vol_scores = self._calc_volatility_scores(result)
        sent_scores = self._calc_sentiment_scores(result)

        result['regime_trend_score'] = trend_scores
        result['regime_vol_score'] = vol_scores
        result['regime_sent_score'] = sent_scores

        # V13: 宏观维度评分 (如果已由 index_analyzer 预计算则直接使用)
        macro_scores = self._get_macro_scores(result)
        result['regime_macro_score'] = macro_scores

        # 分类: 从三维度评分映射到6种状态
        raw_labels = self._classify_regimes(trend_scores, vol_scores, sent_scores)

        # V13: 宏观因子偏置 - 宏观恶化加速识别BEAR, 宏观转好辅助识别底部
        raw_labels = self._apply_macro_bias(raw_labels, trend_scores, macro_scores)

        # V12: 趋势动量偏置 - 捕获趋势快速恶化
        raw_labels = self._apply_momentum_bias(raw_labels, trend_scores)

        # 平滑防抖
        smoothed_labels = self._smooth_regimes(raw_labels)

        result['regime_label'] = smoothed_labels

        # 置信度: 与最近状态中心的距离
        result['regime_score'] = self._calc_confidence(
            trend_scores, vol_scores, sent_scores, smoothed_labels)

        # V21: Regime状态特征增强
        result['regime_duration'] = self._calc_regime_duration(smoothed_labels)
        result['regime_transition_stay'] = self._calc_transition_prob_by_target(
            smoothed_labels, target_label=smoothed_labels, stay=True)
        result['regime_transition_flip'] = self._calc_transition_prob_by_target(
            smoothed_labels, target_label=smoothed_labels, stay=False)

        # 统计
        regime_counts = result['regime_label'].value_counts()
        print(f"[OK] V16 市场状态识别完成")
        for regime, count in regime_counts.items():
            pct = count / len(result) * 100
            print(f"  {regime}: {count}天 ({pct:.1f}%)")

        # V13: 打印宏观维度统计
        if macro_scores.mean() != 50.0:
            print(f"  宏观评分: 均值={macro_scores.mean():.1f}, "
                  f"最新={macro_scores.iloc[-1]:.1f}")

        return result

    # ==================== 趋势维度 ====================

    def _calc_trend_scores(self, df: pd.DataFrame) -> pd.Series:
        """
        趋势维度评分 (0-100)

        子因子:
        - MA50 10日斜率方向 (权重35%)
        - close vs MA50 位置 (权重35%)
        - ADX 方向强度 (权重30%)
        """
        n = len(df)
        scores = pd.Series(50.0, index=df.index)

        close = df.get('close', pd.Series(dtype=float))
        ma50 = df.get('ma_50', pd.Series(dtype=float))
        adx = df.get('adx', pd.Series(dtype=float))
        plus_di = df.get('plus_di', pd.Series(dtype=float))
        minus_di = df.get('minus_di', pd.Series(dtype=float))

        # 1) MA50 斜率: 过去10日MA50的变化率
        ma50_slope = ma50.pct_change(10) * 100  # 百分比变化
        # 映射到 0-100: 正斜率→高分, 负斜率→低分
        # 典型范围约 [-5%, +5%], 映射到 [0, 100]
        slope_score = 50 + ma50_slope.clip(-5, 5) * 10  # [-5,5] → [0,100]
        slope_score = slope_score.fillna(50)

        # 2) Price vs MA50 位置: close/ma50 比值
        price_ratio = close / ma50
        # 典型范围 [0.90, 1.10], 映射到 [0, 100]
        position_score = 50 + (price_ratio - 1.0).clip(-0.10, 0.10) * 500
        position_score = position_score.fillna(50)

        # 3) ADX 方向强度: ADX值 × 方向符号(+DI>-DI为正)
        direction = pd.Series(0.0, index=df.index)
        valid_di = plus_di.notna() & minus_di.notna()
        direction[valid_di & (plus_di > minus_di)] = 1.0
        direction[valid_di & (minus_di > plus_di)] = -1.0

        adx_safe = adx.fillna(15)  # 默认弱趋势
        # ADX范围通常 [10, 60], 乘以方向后 [-60, 60]
        # 映射到 [0, 100]
        adx_score = 50 + direction * adx_safe.clip(0, 50) * 1.0
        adx_score = adx_score.clip(0, 100)

        # 加权合成
        scores = slope_score * 0.35 + position_score * 0.35 + adx_score * 0.30
        scores = scores.clip(0, 100)

        return scores

    # ==================== 波动维度 ====================

    def _calc_volatility_scores(self, df: pd.DataFrame) -> pd.Series:
        """
        波动维度评分 (0-100, 高分=高波动)

        子因子:
        - ATR/close 的滚动百分位 (权重40%)
        - BB宽度/BB中轨 的滚动百分位 (权重35%)
        - 实际波动率 vs 均值 比 (权重25%)
        """
        scores = pd.Series(50.0, index=df.index)
        window = self.lookback_window

        close = df.get('close', pd.Series(dtype=float))
        atr = df.get('atr', pd.Series(dtype=float))
        bb_high = df.get('bb_high', pd.Series(dtype=float))
        bb_low = df.get('bb_low', pd.Series(dtype=float))
        bb_mid = df.get('bb_mid', pd.Series(dtype=float))
        pct_chg = df.get('pct_chg', pd.Series(dtype=float))

        # 1) ATR相对值的百分位
        atr_ratio = atr / close
        atr_pctl = atr_ratio.rolling(window, min_periods=20).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100, raw=False
        ).fillna(50)

        # 2) BB宽度百分位
        bb_width = (bb_high - bb_low) / bb_mid.replace(0, np.nan)
        bb_pctl = bb_width.rolling(window, min_periods=20).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100, raw=False
        ).fillna(50)

        # 3) 实际波动率 / 均值
        realized_vol = pct_chg.rolling(20, min_periods=10).std()
        vol_mean = pct_chg.rolling(window, min_periods=20).std()
        vol_ratio = (realized_vol / vol_mean.replace(0, np.nan)).fillna(1.0)
        # 映射: 比值1.0=50分, 2.0=100分, 0.5=25分
        vol_ratio_score = (vol_ratio.clip(0.3, 2.5) - 0.3) / (2.5 - 0.3) * 100

        # 加权合成
        scores = atr_pctl * 0.40 + bb_pctl * 0.35 + vol_ratio_score * 0.25
        scores = scores.clip(0, 100)

        return scores

    # ==================== 情绪维度 ====================

    def _calc_sentiment_scores(self, df: pd.DataFrame) -> pd.Series:
        """
        情绪/估值维度评分 (0-100, 高分=过热/高估)

        子因子:
        - PE_TTM 百分位 (权重40%)
        - 成交量相对均线 (权重35%)
        - RSI 极端区间 (权重25%)
        """
        scores = pd.Series(50.0, index=df.index)

        rsi = df.get('rsi', pd.Series(dtype=float))
        vol = df.get('vol', pd.Series(dtype=float))
        vol_ma10 = df.get('vol_ma_10', pd.Series(dtype=float))

        # 1) PE_TTM 百分位 (从 percentile_ranks JSON 提取)
        pe_pctl = pd.Series(50.0, index=df.index)
        if 'percentile_ranks' in df.columns:
            pe_pctl = df['percentile_ranks'].apply(
                lambda x: self._extract_json_field(x, 'pe_ttm', 50.0)
            )

        # 2) 成交量 / 均线
        vol_ratio = vol / vol_ma10.replace(0, np.nan)
        vol_ratio = vol_ratio.fillna(1.0)
        # 映射: 1.0=50分, 2.0=90分, 0.5=20分
        vol_score = (vol_ratio.clip(0.3, 3.0) - 0.3) / (3.0 - 0.3) * 100

        # 3) RSI 极端分数: RSI>70或RSI<30表示极端, 映射为高分=过热
        rsi_safe = rsi.fillna(50)
        # RSI直接映射到0-100: RSI=0→0分, RSI=50→50分, RSI=100→100分
        rsi_score = rsi_safe.clip(0, 100)

        # 加权合成
        scores = pe_pctl * 0.40 + vol_score * 0.35 + rsi_score * 0.25
        scores = scores.clip(0, 100)

        return scores

    # ==================== 分类与平滑 ====================

    def _classify_regimes(self,
                          trend: pd.Series,
                          vol: pd.Series,
                          sent: pd.Series) -> pd.Series:
        """
        从三维度评分分类到6种市场状态

        分类优先级(从上到下判定):
        1. HIGH_VOL:   波动极高 + 趋势不明确
        2. BULL_LATE:  有趋势 + 情绪过热
        3. BEAR_LATE:  弱趋势 + 情绪极冷
        4. BULL_TREND: 趋势强 + 波动适中 + 情绪未过热
        5. BEAR_TREND: 趋势弱 + 波动适中
        6. SIDEWAYS:   其余(默认)
        """
        n = len(trend)
        labels = pd.Series(SIDEWAYS, index=trend.index)

        t = self.THRESHOLDS

        # 优先级1: HIGH_VOL
        is_high_vol = (vol > t[HIGH_VOL]['vol_min']) & \
                      (np.abs(trend - 50) < t[HIGH_VOL]['trend_range'])
        labels[is_high_vol] = HIGH_VOL

        # 优先级2: BULL_LATE (牛市末期: 趋势偏上 + 情绪过热)
        is_bull_late = (~is_high_vol) & \
                       (trend > t[BULL_LATE]['trend_min']) & \
                       (sent > t[BULL_LATE]['sent_min'])
        labels[is_bull_late] = BULL_LATE

        # 优先级3: BEAR_LATE (熊市末期: 趋势偏下 + 情绪极冷)
        is_bear_late = (~is_high_vol) & (~is_bull_late) & \
                       (trend < t[BEAR_LATE]['trend_max']) & \
                       (sent < t[BEAR_LATE]['sent_max'])
        labels[is_bear_late] = BEAR_LATE

        # 优先级4: BULL_TREND (强趋势上行 + 波动适中 + 未过热)
        is_bull_trend = (~is_high_vol) & (~is_bull_late) & (~is_bear_late) & \
                        (trend > t[BULL_TREND]['trend_min']) & \
                        (vol < t[BULL_TREND]['vol_max']) & \
                        (sent < t[BULL_TREND]['sent_max'])
        labels[is_bull_trend] = BULL_TREND

        # 优先级5: BEAR_TREND (强趋势下行 + 波动适中)
        is_bear_trend = (~is_high_vol) & (~is_bull_late) & (~is_bear_late) & \
                        (~is_bull_trend) & \
                        (trend < t[BEAR_TREND]['trend_max']) & \
                        (vol < t[BEAR_TREND]['vol_max'])
        labels[is_bear_trend] = BEAR_TREND

        # 其余: SIDEWAYS (已默认)

        return labels

    def _apply_momentum_bias(self, raw_labels: pd.Series,
                              trend_scores: pd.Series) -> pd.Series:
        """
        V12: 趋势动量偏置

        当趋势分数快速下降时, 即使绝对值尚未跌破BEAR_TREND阈值,
        也强制标记为BEAR_TREND。捕获趋势恶化的早期信号。

        仅在趋势已偏弱(trend<35)且加速恶化时触发, 避免误伤震荡市。

        规则:
        1. trend_momentum = trend_scores - trend_scores.shift(lookback)
        2. momentum < -25 且 trend < 35 -> BEAR_TREND (极端恶化)
        3. momentum < -20 且 trend < 35 且当前非BULL类 -> BEAR_TREND
        """
        labels = raw_labels.copy()
        lookback = self.momentum_lookback

        trend_momentum = trend_scores - trend_scores.shift(lookback)

        # 仅覆盖非BULL类状态 (避免在牛市回调时误判)
        not_bull = ~labels.isin([BULL_TREND, BULL_LATE])

        # 强偏置: 趋势极端恶化 + 趋势已弱
        strong_bias = (trend_momentum < self.momentum_bear_threshold) & \
                      (trend_scores < 35)
        labels[strong_bias] = BEAR_TREND

        # 中等偏置: 趋势中速恶化 + 趋势弱 + 非牛市
        moderate_bias = not_bull & \
                        (trend_momentum < self.momentum_bear_threshold + 5) & \
                        (trend_scores < 35)
        labels[moderate_bias] = BEAR_TREND

        n_overridden = strong_bias.sum() + moderate_bias.sum()
        if n_overridden > 0:
            print(f"  V16 动量偏置: {n_overridden}天覆盖为BEAR_TREND")

        return labels

    def _smooth_regimes(self, raw_labels: pd.Series) -> pd.Series:
        """
        平滑防抖: 5日众数平滑 + 最小持续天数过滤

        防止在状态边界频繁跳变
        """
        if len(raw_labels) <= self.smooth_window:
            return raw_labels

        # 5日众数平滑
        smoothed = raw_labels.copy()
        for i in range(self.smooth_window, len(raw_labels)):
            window = raw_labels.iloc[max(0, i - self.smooth_window + 1):i + 1]
            mode_val = window.mode()
            if len(mode_val) > 0:
                smoothed.iloc[i] = mode_val.iloc[0]

        # 最小持续天数过滤: 如果新状态持续不到min_persist_days, 恢复为前一状态
        if self.min_persist_days > 1:
            filtered = smoothed.copy()
            current_regime = filtered.iloc[0]
            regime_start = 0

            for i in range(1, len(filtered)):
                if filtered.iloc[i] != current_regime:
                    # 状态切换, 检查前一段是否持续足够
                    duration = i - regime_start
                    if duration < self.min_persist_days and regime_start > 0:
                        # 太短, 恢复为再前一个状态
                        prev_regime = filtered.iloc[max(0, regime_start - 1)]
                        filtered.iloc[regime_start:i] = prev_regime
                    current_regime = filtered.iloc[i]
                    regime_start = i

            smoothed = filtered

        return smoothed

    # ==================== 置信度 ====================

    def _calc_confidence(self,
                         trend: pd.Series,
                         vol: pd.Series,
                         sent: pd.Series,
                         labels: pd.Series) -> pd.Series:
        """
        计算每个时间点的状态置信度 (0-100)

        置信度越高，表示三维度评分越明确地指向当前状态
        """
        confidence = pd.Series(50.0, index=labels.index)

        # 状态中心点 (理想的三维度评分)
        centers = {
            BULL_TREND: (80, 40, 55),
            BULL_LATE:  (65, 55, 85),
            BEAR_TREND: (20, 40, 45),
            BEAR_LATE:  (30, 45, 15),
            SIDEWAYS:   (50, 45, 50),
            HIGH_VOL:   (50, 85, 55),
        }

        for regime, (ct, cv, cs) in centers.items():
            mask = labels == regime
            if mask.sum() == 0:
                continue
            # 欧氏距离越小→置信度越高
            dist = np.sqrt(
                (trend[mask] - ct) ** 2 +
                (vol[mask] - cv) ** 2 +
                (sent[mask] - cs) ** 2
            )
            # 最大可能距离约 ~173 (三维各差100)
            conf = (1 - dist / 173) * 100
            confidence[mask] = conf.clip(0, 100)

        return confidence

    # ==================== V13: 宏观维度 ====================

    def _get_macro_scores(self, df: pd.DataFrame) -> pd.Series:
        """
        获取宏观维度评分

        如果 DataFrame 中已有 macro_score 列 (由 index_analyzer 预计算)，
        直接使用；否则返回中性值 50。
        """
        if 'macro_score' in df.columns:
            return pd.to_numeric(df['macro_score'], errors='coerce').fillna(50.0)
        return pd.Series(50.0, index=df.index)

    def _apply_macro_bias(self, raw_labels: pd.Series,
                           trend_scores: pd.Series,
                           macro_scores: pd.Series) -> pd.Series:
        """
        V13: 宏观因子偏置

        宏观环境恶化时加速识别熊市，宏观环境转好时辅助识别底部。

        规则:
        1. 宏观极差(macro<30) + 趋势偏弱(trend<45) + 非BULL类 -> BEAR_TREND
           (宏观资金面收紧 + 利率上行 + 北向资金流出 + 人民币贬值)
        2. 宏观极好(macro>70) + 趋势极弱(trend<30) + 当前BEAR_TREND -> BEAR_LATE
           (宏观底部信号: 利率开始下行 + 资金回流，辅助判断熊市尾声)

        仅在宏观数据有效时触发 (macro_scores 不全为50)
        """
        labels = raw_labels.copy()

        # 检查是否有有效的宏观数据
        if macro_scores.std() < 1.0:
            # 宏观数据全为50 (无数据), 不做偏置
            return labels

        not_bull = ~labels.isin([BULL_TREND, BULL_LATE])

        # 规则1: 宏观恶化 + 趋势偏弱 -> BEAR_TREND
        macro_bearish = (macro_scores < 30) & (trend_scores < 45) & not_bull
        n_bear_override = macro_bearish.sum()
        labels[macro_bearish] = BEAR_TREND

        # 规则2: 宏观转好 + 趋势极弱 + 当前BEAR -> BEAR_LATE (辅助识别底部)
        is_bear = labels == BEAR_TREND
        macro_bullish_bottom = (macro_scores > 70) & (trend_scores < 30) & is_bear
        n_late_override = macro_bullish_bottom.sum()
        labels[macro_bullish_bottom] = BEAR_LATE

        if n_bear_override > 0 or n_late_override > 0:
            print(f"  V16 宏观偏置: {n_bear_override}天->BEAR_TREND, "
                  f"{n_late_override}天->BEAR_LATE")

        return labels

    # ==================== V21: Regime特征增强 ====================

    @staticmethod
    def _calc_regime_duration(labels: pd.Series) -> pd.Series:
        """
        计算连续同状态持续天数

        对 regime_label 序列进行连续分组计数，
        每组第一天为1，第二天为2，以此类推。
        状态变化时重置为1。
        """
        # 创建变化点标记: 当前不等于前一个 → 新状态开始
        change_points = labels != labels.shift(1)
        # 对每个分组编号 (变化点累计和)
        group_ids = change_points.cumsum()
        # 组内计数
        duration = group_ids.groupby(group_ids).cumcount() + 1
        # 第一天 (change_points 为 NaN 的 shift) 设为1
        duration = duration.fillna(1).astype(int)
        return duration

    @staticmethod
    def _calc_transition_prob_by_target(
        labels: pd.Series,
        target_label: pd.Series,
        stay: bool = True,
        window: int = 60,
        min_samples: int = 10,
    ) -> pd.Series:
        """
        计算给定状态下"停留"或"切换"的历史概率

        Args:
            labels: regime_label 序列
            target_label: 目标状态序列 (用于逐行判断当前状态)
            stay: True=计算同一状态延续概率, False=计算切换为其他状态概率
            window: 滚动窗口大小
            min_samples: 最少样本要求

        Returns:
            pd.Series: 0-100 概率值
        """
        result = pd.Series(50.0, index=labels.index)  # 默认中性

        for i in range(window, len(labels)):
            current_state = target_label.iloc[i]
            if pd.isna(current_state):
                continue

            # 取前 window 天中同样状态的日子的后续一天
            past_window = labels.iloc[i - window:i]
            same_state_mask = past_window.iloc[:-1] == current_state
            n_same = same_state_mask.sum()

            if n_same < min_samples:
                continue  # 样本不足，保持中性

            # 关注这些相同状态日的次日状态
            next_states = past_window.iloc[1:][same_state_mask.values]

            if stay:
                # 计算停留概率 (次日状态不变)
                n_stay = (next_states == current_state).sum()
                prob = n_stay / n_same * 100
            else:
                # 计算切换概率 (次日状态变化)
                n_flip = (next_states != current_state).sum()
                prob = n_flip / n_same * 100

            result.iloc[i] = prob

        return result

    # ==================== 工具方法 ====================

    @staticmethod
    def _extract_json_field(json_str, field: str, default: float = 50.0) -> float:
        """从 JSON 字符串中提取字段值"""
        if pd.isna(json_str) or not json_str:
            return default
        try:
            if isinstance(json_str, str):
                data = json.loads(json_str)
            elif isinstance(json_str, dict):
                data = json_str
            else:
                return default
            val = data.get(field, default)
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return default
            return float(val)
        except (json.JSONDecodeError, TypeError, ValueError):
            return default

    @staticmethod
    def get_consensus_thresholds(regime_label: str) -> Dict[str, int]:
        """获取指定状态的共识投票阈值"""
        return CONSENSUS_THRESHOLDS.get(regime_label, CONSENSUS_THRESHOLDS[SIDEWAYS])

    @staticmethod
    def get_factor_weights(regime_label: str) -> Dict[str, float]:
        """获取指定状态的多因子权重"""
        return FACTOR_WEIGHTS_BY_REGIME.get(regime_label, FACTOR_WEIGHTS_BY_REGIME[SIDEWAYS])
