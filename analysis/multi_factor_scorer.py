"""
多因子综合评分模块

基于五维因子（趋势、动量、成交量、估值、波动率）对指数进行综合评分，
结合趋势状态判断生成买卖信号，用于指导ETF日线级别投资。
"""

import json
from typing import Optional, Dict, Tuple

import numpy as np
import pandas as pd


class MultiFactorScorer:
    """
    多因子综合评分器

    五维因子:
    - 趋势因子 (30%): 均线排列、价格vs均线、MACD方向、ADX趋势强度
    - 动量因子 (25%): RSI位置、KDJ位置、RSI趋势
    - 成交量因子 (15%): 量价配合、OBV趋势、成交量位置
    - 估值因子 (20%): PE百分位、PB百分位
    - 波动率因子 (10%): 布林带位置、ATR相对值

    使用示例:
        scorer = MultiFactorScorer()
        df = scorer.calculate(df)
        # df 新增列: factor_score, factor_signal, trend_state, factor_detail
    """

    DEFAULT_WEIGHTS = {
        'trend': 0.30,
        'momentum': 0.25,
        'volume': 0.15,
        'valuation': 0.20,
        'volatility': 0.10
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Args:
            weights: 各因子权重字典，键为 trend/momentum/volume/valuation/volatility
        """
        self.weights = weights or self.DEFAULT_WEIGHTS

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算多因子评分和买卖信号

        V8: 如果 df 包含 regime_label 列，动态切换各因子权重

        Args:
            df: 包含技术指标的 DataFrame (需要已计算好所有指标)

        Returns:
            pd.DataFrame: 新增 factor_score, factor_signal, trend_state, factor_detail 列
        """
        result_df = df.copy()

        # V8: 检查是否有regime信息
        has_regime = 'regime_label' in result_df.columns
        regime_weights_map = None
        if has_regime:
            from analysis.market_regime_detector import MarketRegimeDetector, FACTOR_WEIGHTS_BY_REGIME
            regime_weights_map = FACTOR_WEIGHTS_BY_REGIME

        scores_list = []
        signals_list = []
        trend_states_list = []
        details_list = []

        for i in range(len(result_df)):
            row = result_df.iloc[i]

            # V8: 根据当前行的regime动态选择权重
            if has_regime and regime_weights_map:
                regime_label = row.get('regime_label', None)
                if regime_label and regime_label in regime_weights_map:
                    current_weights = regime_weights_map[regime_label]
                else:
                    current_weights = self.weights
            else:
                current_weights = self.weights

            scores, total_score = self._calculate_all_scores(row, result_df, i, current_weights)
            trend_state = self._determine_trend_state(row)
            signal, confidence = self._generate_signal(total_score, trend_state)

            scores_list.append(total_score)
            signals_list.append(signal)
            trend_states_list.append(trend_state)
            details_list.append(json.dumps(scores, ensure_ascii=False))

        result_df['factor_score'] = scores_list
        result_df['factor_signal'] = signals_list
        result_df['trend_state'] = trend_states_list
        result_df['factor_detail'] = details_list

        return result_df

    # ==================== 综合评分 ====================

    def _calculate_all_scores(self, row: pd.Series, df: pd.DataFrame,
                              idx: int, weights: Optional[Dict[str, float]] = None) -> Tuple[dict, float]:
        """计算所有因子评分并返回加权总分

        Args:
            row: 当前行数据
            df: 完整 DataFrame
            idx: 当前行索引
            weights: V8动态权重，为None时使用self.weights
        """
        w = weights or self.weights

        trend_score = self._score_trend(row)
        momentum_score = self._score_momentum(row, df, idx)
        volume_score = self._score_volume(row, df, idx)
        valuation_score = self._score_valuation(row)
        volatility_score = self._score_volatility(row, df, idx)

        scores = {
            'trend': round(trend_score, 1),
            'momentum': round(momentum_score, 1),
            'volume': round(volume_score, 1),
            'valuation': round(valuation_score, 1),
            'volatility': round(volatility_score, 1),
        }

        total_score = (
            trend_score * w['trend']
            + momentum_score * w['momentum']
            + volume_score * w['volume']
            + valuation_score * w['valuation']
            + volatility_score * w['volatility']
        )
        total_score = max(0.0, min(100.0, total_score))

        return scores, round(total_score, 1)

    # ==================== 趋势因子 ====================

    def _score_trend(self, row: pd.Series) -> float:
        """趋势因子评分 (0-100)"""
        ma_arrangement = self._score_ma_arrangement(row)
        price_vs_ma = self._score_price_vs_ma(row)
        macd_direction = self._score_macd_direction(row)
        adx_strength = self._score_adx_strength(row)

        return (ma_arrangement * 0.30
                + price_vs_ma * 0.25
                + macd_direction * 0.25
                + adx_strength * 0.20)

    def _score_ma_arrangement(self, row: pd.Series) -> float:
        """均线排列评分: 多头排列=100, 空头排列=0"""
        ma5 = row.get('ma_5')
        ma10 = row.get('ma_10')
        ma20 = row.get('ma_20')
        ma50 = row.get('ma_50')
        if self._any_nan(ma5, ma10, ma20, ma50):
            return 50.0

        pairs = [(ma5, ma10), (ma10, ma20), (ma20, ma50)]
        bullish_count = sum(1 for short, long in pairs if short > long)
        return bullish_count / 3.0 * 100.0

    def _score_price_vs_ma(self, row: pd.Series) -> float:
        """价格相对均线位置: 在各均线上方各+25分"""
        close = row.get('close')
        if self._is_nan(close):
            return 50.0

        score = 0.0
        for ma_col in ['ma_50', 'ma_20', 'ma_10', 'ma_5']:
            ma_val = row.get(ma_col)
            if not self._is_nan(ma_val) and close > ma_val:
                score += 25.0
        return score

    def _score_macd_direction(self, row: pd.Series) -> float:
        """MACD方向评分: 红柱变长=90, 红柱变短=65, 绿柱变短=45, 绿柱变长=15"""
        hist = row.get('macd_histogram')
        cross_signals_str = row.get('cross_signals')

        if self._is_nan(hist):
            return 50.0

        hist_trend = None
        if cross_signals_str and isinstance(cross_signals_str, str):
            try:
                signals = json.loads(cross_signals_str)
                hist_trend = signals.get('macd_hist_trend')
            except (json.JSONDecodeError, TypeError):
                pass

        if hist_trend == 'red_longer':
            return 90.0
        elif hist_trend == 'red_shorter':
            return 65.0
        elif hist_trend == 'green_shorter':
            return 45.0
        elif hist_trend == 'green_longer':
            return 15.0

        # 降级: 仅看柱状图正负
        if hist > 0:
            return 70.0
        else:
            return 30.0

    def _score_adx_strength(self, row: pd.Series) -> float:
        """ADX趋势强度评分"""
        adx = row.get('adx')
        if self._is_nan(adx):
            return 50.0

        plus_di = row.get('plus_di')
        minus_di = row.get('minus_di')
        di_bullish = (not self._is_nan(plus_di) and not self._is_nan(minus_di)
                      and plus_di > minus_di)

        if adx > 40:
            return 100.0 if di_bullish else 40.0
        elif adx > 25:
            return 80.0 if di_bullish else 45.0
        elif adx > 20:
            return 50.0
        else:
            return 30.0

    # ==================== 动量因子 ====================

    def _score_momentum(self, row: pd.Series, df: pd.DataFrame, idx: int) -> float:
        """动量因子评分 (0-100)"""
        rsi_position = self._score_rsi_position(row)
        kdj_position = self._score_kdj_position(row)
        rsi_trend = self._score_rsi_trend(df, idx)

        return (rsi_position * 0.45
                + kdj_position * 0.35
                + rsi_trend * 0.20)

    def _score_rsi_position(self, row: pd.Series) -> float:
        """RSI位置评分: 超卖区间得高分(适合买入)"""
        rsi = row.get('rsi')
        if self._is_nan(rsi):
            return 50.0

        if rsi < 30:
            return 95.0
        elif rsi < 40:
            return 75.0
        elif rsi < 60:
            return 50.0
        elif rsi < 70:
            return 25.0
        else:
            return 5.0

    def _score_kdj_position(self, row: pd.Series) -> float:
        """KDJ J值位置评分: 超卖区间得高分"""
        j = row.get('kdj_j')
        if self._is_nan(j):
            return 50.0

        if j < 0:
            return 95.0
        elif j < 20:
            return 75.0
        elif j < 80:
            return 50.0
        elif j < 100:
            return 25.0
        else:
            return 5.0

    def _score_rsi_trend(self, df: pd.DataFrame, idx: int) -> float:
        """RSI近5日趋势: 上升=70, 持平=50, 下降=30"""
        if idx < 5:
            return 50.0

        rsi_now = df.iloc[idx].get('rsi')
        rsi_5d_ago = df.iloc[idx - 5].get('rsi')
        if self._is_nan(rsi_now) or self._is_nan(rsi_5d_ago):
            return 50.0

        diff = rsi_now - rsi_5d_ago
        if diff > 3:
            return 70.0
        elif diff < -3:
            return 30.0
        else:
            return 50.0

    # ==================== 成交量因子 ====================

    def _score_volume(self, row: pd.Series, df: pd.DataFrame, idx: int) -> float:
        """成交量因子评分 (0-100)"""
        vol_price = self._score_volume_price(row)
        obv_trend = self._score_obv_trend(df, idx)
        vol_position = self._score_vol_position(row)

        return (vol_price * 0.40
                + obv_trend * 0.35
                + vol_position * 0.25)

    def _score_volume_price(self, row: pd.Series) -> float:
        """量价配合评分"""
        pct_chg = row.get('pct_chg')
        vol = row.get('vol')
        vol_ma5 = row.get('vol_ma_5')

        if self._any_nan(pct_chg, vol, vol_ma5) or vol_ma5 == 0:
            return 50.0

        vol_ratio = vol / vol_ma5
        is_up = pct_chg > 0
        is_high_vol = vol_ratio > 1.2

        if is_up and is_high_vol:
            return 95.0   # 放量上涨
        elif is_up and not is_high_vol:
            return 75.0   # 缩量上涨
        elif not is_up and not is_high_vol:
            return 35.0   # 缩量下跌
        else:
            return 10.0   # 放量下跌

    def _score_obv_trend(self, df: pd.DataFrame, idx: int) -> float:
        """OBV 5日趋势评分"""
        if idx < 5:
            return 50.0

        obv_now = df.iloc[idx].get('obv')
        obv_5d = df.iloc[idx - 5].get('obv')
        if self._any_nan(obv_now, obv_5d):
            return 50.0

        # 还要看 OBV 是在上升中还是下降中
        obv_mid = df.iloc[idx - 2].get('obv') if idx >= 2 else obv_5d

        slope = obv_now - obv_5d
        accelerating = (obv_now - obv_mid) > (obv_mid - obv_5d) if not self._is_nan(obv_mid) else False

        if slope > 0 and accelerating:
            return 85.0
        elif slope > 0:
            return 65.0
        elif slope < 0 and not accelerating:
            return 20.0
        else:
            return 45.0

    def _score_vol_position(self, row: pd.Series) -> float:
        """成交量相对均线位置评分"""
        vol = row.get('vol')
        vol_ma5 = row.get('vol_ma_5')
        pct_chg = row.get('pct_chg')

        if self._any_nan(vol, vol_ma5) or vol_ma5 == 0:
            return 50.0

        vol_ratio = vol / vol_ma5
        is_up = pct_chg > 0 if not self._is_nan(pct_chg) else True

        if vol_ratio > 1.5:
            return 80.0 if is_up else 20.0
        elif vol_ratio < 0.7:
            return 60.0 if is_up else 40.0
        else:
            return 50.0

    # ==================== 估值因子 ====================

    def _score_valuation(self, row: pd.Series) -> float:
        """估值因子评分 (0-100): 低估值=高分"""
        pe_pctl = self._get_percentile(row, 'pe_ttm')
        pb_pctl = self._get_percentile(row, 'pb')

        pe_score = self._percentile_to_score(pe_pctl)
        pb_score = self._percentile_to_score(pb_pctl)

        return pe_score * 0.60 + pb_score * 0.40

    def _get_percentile(self, row: pd.Series, key: str) -> Optional[float]:
        """从 percentile_ranks JSON 中提取百分位值"""
        pr_str = row.get('percentile_ranks')
        if not pr_str or not isinstance(pr_str, str):
            return None
        try:
            pr_dict = json.loads(pr_str)
            val = pr_dict.get(key)
            return float(val) if val is not None else None
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

    @staticmethod
    def _percentile_to_score(pctl: Optional[float]) -> float:
        """百分位转评分: 低百分位=高分(低估值是买入信号)"""
        if pctl is None:
            return 50.0
        if pctl < 10:
            return 100.0
        elif pctl < 25:
            return 85.0
        elif pctl < 50:
            return 60.0
        elif pctl < 75:
            return 35.0
        else:
            return 10.0

    # ==================== 波动率因子 ====================

    def _score_volatility(self, row: pd.Series, df: pd.DataFrame, idx: int) -> float:
        """波动率因子评分 (0-100)"""
        bb_score = self._score_bollinger_position(row)
        atr_score = self._score_atr_relative(row, df, idx)

        return bb_score * 0.60 + atr_score * 0.40

    def _score_bollinger_position(self, row: pd.Series) -> float:
        """布林带位置评分: 接近下轨得高分"""
        close = row.get('close')
        bb_high = row.get('bb_high')
        bb_low = row.get('bb_low')

        if self._any_nan(close, bb_high, bb_low):
            return 50.0

        bb_width = bb_high - bb_low
        if bb_width <= 0:
            return 50.0

        position = (close - bb_low) / bb_width

        if position < 0.2:
            return 90.0
        elif position < 0.4:
            return 70.0
        elif position < 0.6:
            return 50.0
        elif position < 0.8:
            return 30.0
        else:
            return 10.0

    def _score_atr_relative(self, row: pd.Series, df: pd.DataFrame, idx: int) -> float:
        """ATR相对值评分: 低波动=高分"""
        atr = row.get('atr')
        close = row.get('close')

        if self._any_nan(atr, close) or close == 0:
            return 50.0

        atr_ratio = atr / close

        # 用过去50日的ATR比值计算百分位
        lookback = min(50, idx)
        if lookback < 10:
            return 50.0

        historical_ratios = []
        for j in range(idx - lookback, idx):
            h_atr = df.iloc[j].get('atr')
            h_close = df.iloc[j].get('close')
            if not self._any_nan(h_atr, h_close) and h_close != 0:
                historical_ratios.append(h_atr / h_close)

        if len(historical_ratios) < 10:
            return 50.0

        pctl = sum(1 for r in historical_ratios if r < atr_ratio) / len(historical_ratios) * 100

        # 低波动 (低百分位) = 高分
        if pctl < 20:
            return 85.0
        elif pctl < 40:
            return 70.0
        elif pctl < 60:
            return 50.0
        elif pctl < 80:
            return 30.0
        else:
            return 15.0

    # ==================== 趋势状态判断 ====================

    def _determine_trend_state(self, row: pd.Series) -> str:
        """
        判断当前趋势状态

        Returns:
            'uptrend' / 'downtrend' / 'sideways'
        """
        adx = row.get('adx')
        ma5 = row.get('ma_5')
        ma10 = row.get('ma_10')
        ma20 = row.get('ma_20')

        has_adx = not self._is_nan(adx)
        has_ma = not self._any_nan(ma5, ma10, ma20)

        if not has_ma:
            return 'sideways'

        ma_bullish = ma5 > ma10 > ma20
        ma_bearish = ma5 < ma10 < ma20

        if has_adx and adx > 25:
            if ma_bullish:
                return 'uptrend'
            elif ma_bearish:
                return 'downtrend'

        # ADX 弱或无 ADX 时，仅靠均线做弱判断
        if not has_adx:
            if ma_bullish:
                return 'uptrend'
            elif ma_bearish:
                return 'downtrend'

        return 'sideways'

    # ==================== 信号生成 ====================

    def _generate_signal(self, total_score: float, trend_state: str) -> Tuple[str, float]:
        """
        基于综合评分和趋势状态生成信号 (V7-4 信号阈值优化)

        优化目标: 增加BUY/SELL信号频率，从原来的1.8%提升至10-15%

        Returns:
            (signal, confidence): signal 为 BUY/SELL/HOLD
        """
        # V7-4: 调整信号阈值以增加信号频率
        # 默认阈值过于保守，导致98.2%信号为HOLD
        # 优化后目标: BUY/SELL信号比例提升至20-30%

        if trend_state == 'uptrend':
            # uptrend: 降低BUY阈值，提高SELL阈值
            if total_score >= 55:
                return 'BUY', total_score / 100.0
            elif total_score < 45:
                return 'HOLD', 0.5
            else:
                return 'HOLD', 0.5
        elif trend_state == 'downtrend':
            # downtrend: 降低BUY阈值，保持SELL阈值
            if total_score >= 60:
                return 'HOLD', 0.4
            elif total_score < 35:
                return 'SELL', (100 - total_score) / 100.0
            else:
                return 'HOLD', 0.4
        else:  # sideways
            # sideways: 降低BUY阈值，提高SELL阈值
            if total_score >= 60:
                return 'BUY', total_score / 100.0
            elif total_score < 40:
                return 'SELL', (100 - total_score) / 100.0
            else:
                return 'HOLD', 0.5

    # ==================== 工具方法 ====================

    @staticmethod
    def _is_nan(value) -> bool:
        if value is None:
            return True
        try:
            return np.isnan(float(value))
        except (TypeError, ValueError):
            return True

    @classmethod
    def _any_nan(cls, *values) -> bool:
        return any(cls._is_nan(v) for v in values)
