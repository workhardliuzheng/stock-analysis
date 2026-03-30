"""
信号整合器

整合多因子评分信号和机器学习预测信号，生成最终的买卖信号。
支持回归模型输出 (ml_predicted_return) 和分类模型输出 (ml_probability)。
"""

import numpy as np
import pandas as pd


class SignalGenerator:
    """
    信号整合器

    融合 MultiFactorScorer 和 MLPredictor 两路信号，
    基于趋势状态 + 评分 + ML预测生成最终 BUY/SELL/HOLD 信号。

    前置条件:
        df 中需包含以下列 (由 MultiFactorScorer 和 MLPredictor 生成):
        - factor_score: 多因子综合评分 (0-100)
        - factor_signal: 多因子信号 (BUY/SELL/HOLD)
        - trend_state: 趋势状态 (uptrend/downtrend/sideways)
        - ml_probability: ML上涨伪概率 (0-1)
        - ml_signal: ML信号 (BUY/SELL/HOLD)
        - ml_predicted_return: ML预测收益率 (可选, 回归模型输出)

    使用示例:
        generator = SignalGenerator()
        df = generator.generate(df)
        # df 新增列: final_signal, final_confidence
    """

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成最终信号

        Args:
            df: 包含多因子和ML预测结果的 DataFrame

        Returns:
            pd.DataFrame: 新增 final_signal 和 final_confidence 列
        """
        result = df.copy()

        signals = []
        confidences = []

        for i in range(len(result)):
            row = result.iloc[i]
            signal, confidence = self._fuse_signal(row)
            signals.append(signal)
            confidences.append(confidence)

        result['final_signal'] = signals
        result['final_confidence'] = confidences
        return result

    def _fuse_signal(self, row: pd.Series) -> tuple:
        """
        融合两路信号

        Returns:
            (signal, confidence)
        """
        trend_state = row.get('trend_state', 'sideways')
        factor_score = row.get('factor_score', 50.0)
        factor_signal = row.get('factor_signal', 'HOLD')
        ml_prob = row.get('ml_probability', 0.5)
        ml_pred_ret = row.get('ml_predicted_return', None)

        if self._is_nan(ml_prob):
            ml_prob = 0.5

        # 读取自适应阈值（由 MLPredictor 生成），如不存在则使用默认值
        buy_thresh = row.get('ml_buy_threshold', 0.1)
        sell_thresh = row.get('ml_sell_threshold', -0.1)
        if self._is_nan(buy_thresh):
            buy_thresh = 0.1
        if self._is_nan(sell_thresh):
            sell_thresh = -0.1

        # 判断 ML 看多/看空
        # 优先使用预测收益率（回归模型），回退到伪概率
        if ml_pred_ret is not None and not self._is_nan(ml_pred_ret):
            ml_bullish = ml_pred_ret > buy_thresh
            ml_bearish = ml_pred_ret < sell_thresh
        else:
            ml_bullish = ml_prob > 0.55
            ml_bearish = ml_prob < 0.45

        factor_buy = factor_signal == 'BUY'
        factor_sell = factor_signal == 'SELL'

        # 信号融合
        if trend_state == 'uptrend':
            if ml_bullish and factor_buy:
                signal = 'BUY'       # 强买入: 趋势上行 + 两路信号一致
            elif ml_bullish or factor_buy:
                signal = 'BUY'       # 买入: 趋势上行 + 至少一路看多
            elif ml_bearish and factor_sell:
                signal = 'SELL'      # 上行趋势中两路都看空，卖出
            else:
                signal = 'HOLD'
        elif trend_state == 'downtrend':
            if ml_bearish and factor_sell:
                signal = 'SELL'      # 强卖出: 趋势下行 + 两路信号一致
            elif ml_bearish or factor_sell:
                signal = 'SELL'      # 卖出: 趋势下行 + 至少一路看空
            elif ml_bullish and factor_buy:
                signal = 'HOLD'      # 下行趋势中两路都看多，但不急于买入
            else:
                signal = 'HOLD'
        else:  # sideways
            if ml_bullish and factor_buy:
                signal = 'BUY'
            elif ml_bearish and factor_sell:
                signal = 'SELL'
            else:
                signal = 'HOLD'

        # 置信度: 多因子40% + ML 60%
        confidence = factor_score / 100.0 * 0.4 + ml_prob * 0.6
        confidence = max(0.0, min(1.0, confidence))

        return signal, round(confidence, 3)

    @staticmethod
    def _is_nan(value) -> bool:
        if value is None:
            return True
        try:
            return np.isnan(float(value))
        except (TypeError, ValueError):
            return True
