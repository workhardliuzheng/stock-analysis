"""
V13 宏观因子评分器

将宏观经济数据转换为 0-100 的综合评分，反映宏观环境对股市的利好/利空程度。

四个子因子:
1. 利率因子 (权重30%): Shibor下行=利好(高分), 上行=利空(低分)
2. 资金流向因子 (权重30%): 北向资金净流入=利好(高分)
3. 杠杆情绪因子 (权重20%): 融资余额增长=乐观(高分)
4. 汇率因子 (权重20%): 人民币升值=利好(高分)

输出:
- macro_score (0-100): 综合宏观评分
- macro_rate_score (0-100): 利率子分数
- macro_flow_score (0-100): 资金流向子分数
- macro_leverage_score (0-100): 杠杆情绪子分数
- macro_fx_score (0-100): 汇率子分数

设计原则:
1. 仅使用当天及之前数据 (无未来泄露)
2. 使用滚动百分位归一化，适应不同市场阶段
3. 缺失数据源给50分 (中性)，不影响其他子因子
"""

import numpy as np
import pandas as pd
from typing import Optional


class MacroFactorScorer:
    """
    宏观因子评分器

    使用示例:
        scorer = MacroFactorScorer()
        df = scorer.score(df)  # df 需包含宏观数据列
        # df 新增: macro_score, macro_rate_score, macro_flow_score,
        #          macro_leverage_score, macro_fx_score
    """

    # 子因子权重
    WEIGHTS = {
        'rate': 0.30,       # 利率因子
        'flow': 0.30,       # 资金流向因子
        'leverage': 0.20,   # 杠杆情绪因子
        'fx': 0.20,         # 汇率因子
    }

    def __init__(self,
                 lookback_window: int = 120,
                 weights: Optional[dict] = None):
        """
        Args:
            lookback_window: 滚动百分位计算窗口 (交易日)
            weights: 自定义子因子权重 (可选)
        """
        self.lookback_window = lookback_window
        if weights:
            self.WEIGHTS = weights

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算宏观因子综合评分

        Args:
            df: 包含宏观数据列的 DataFrame

        Returns:
            DataFrame: 新增 macro_score 等列
        """
        result = df.copy()

        # 计算各子因子评分
        rate_score = self._score_rate(result)
        flow_score = self._score_flow(result)
        leverage_score = self._score_leverage(result)
        fx_score = self._score_fx(result)

        result['macro_rate_score'] = rate_score
        result['macro_flow_score'] = flow_score
        result['macro_leverage_score'] = leverage_score
        result['macro_fx_score'] = fx_score

        # 加权合成
        result['macro_score'] = (
            rate_score * self.WEIGHTS['rate'] +
            flow_score * self.WEIGHTS['flow'] +
            leverage_score * self.WEIGHTS['leverage'] +
            fx_score * self.WEIGHTS['fx']
        ).clip(0, 100)

        # 统计
        valid_count = result['macro_score'].notna().sum()
        if valid_count > 0:
            avg_score = result['macro_score'].mean()
            latest = result['macro_score'].iloc[-1] if len(result) > 0 else 50
            print(f"  [V16] 宏观因子评分完成: "
                  f"最新={latest:.1f}, 均值={avg_score:.1f}, "
                  f"利率={rate_score.iloc[-1]:.1f}, "
                  f"资金流向={flow_score.iloc[-1]:.1f}, "
                  f"杠杆={leverage_score.iloc[-1]:.1f}, "
                  f"汇率={fx_score.iloc[-1]:.1f}")

        return result

    # ==================== 利率因子 ====================

    def _score_rate(self, df: pd.DataFrame) -> pd.Series:
        """
        利率因子评分 (0-100)

        高分 = 利好 (利率下行/低位)
        低分 = 利空 (利率上行/高位)

        子因子:
        - Shibor 隔夜利率水平 (反向，低利率=高分) (40%)
        - Shibor 10日变化 (反向，下行=高分) (35%)
        - 期限利差 (正常=高分, 倒挂=低分) (25%)
        """
        scores = pd.Series(50.0, index=df.index)

        has_shibor = 'shibor_on' in df.columns

        if not has_shibor:
            return scores

        # 1) Shibor隔夜利率水平 -> 滚动百分位 (反向: 低利率=高分)
        shibor_level = self._rolling_percentile(df['shibor_on'])
        shibor_level_score = 100 - shibor_level  # 反向

        # 2) Shibor 10日变化 (反向: 下行=高分)
        chg10_score = pd.Series(50.0, index=df.index)
        if 'shibor_on_chg10' in df.columns:
            shibor_chg10 = df['shibor_on_chg10']
            # 变化范围通常 [-1%, +1%], 映射到 [0, 100]
            chg10_score = 50 - shibor_chg10.clip(-1, 1) * 50  # 下行=高分
            chg10_score = chg10_score.fillna(50).clip(0, 100)

        # 3) 期限利差 (1m - on, 正常为正, 倒挂为负)
        spread_score = pd.Series(50.0, index=df.index)
        if 'shibor_term_spread' in df.columns:
            spread = df['shibor_term_spread']
            # 正常利差(正) -> 高分, 倒挂(负) -> 低分
            spread_score = 50 + spread.clip(-1, 1) * 25
            spread_score = spread_score.fillna(50).clip(0, 100)

        scores = shibor_level_score * 0.40 + chg10_score * 0.35 + spread_score * 0.25
        return scores.clip(0, 100)

    # ==================== 资金流向因子 ====================

    def _score_flow(self, df: pd.DataFrame) -> pd.Series:
        """
        资金流向因子评分 (0-100)

        高分 = 利好 (北向资金持续净流入)
        低分 = 利空 (北向资金持续净流出)

        子因子:
        - 北向资金 20日累计净流入的滚动百分位 (50%)
        - 北向资金 5日累计方向 (连续流入=高分) (30%)
        - 北向资金 当日净流入强度 (20%)
        """
        scores = pd.Series(50.0, index=df.index)

        has_north = 'north_money' in df.columns

        if not has_north:
            return scores

        # 1) 20日累计净流入的百分位
        cumul20_score = pd.Series(50.0, index=df.index)
        if 'north_money_20d' in df.columns:
            cumul20_score = self._rolling_percentile(df['north_money_20d'])

        # 2) 5日累计方向 (连续流入天数比例)
        flow5_score = pd.Series(50.0, index=df.index)
        if 'north_money_5d' in df.columns:
            # 5日累计净流入百分位
            flow5_score = self._rolling_percentile(df['north_money_5d'])

        # 3) 当日净流入强度百分位
        daily_score = self._rolling_percentile(df['north_money'])

        scores = cumul20_score * 0.50 + flow5_score * 0.30 + daily_score * 0.20
        return scores.clip(0, 100)

    # ==================== 杠杆情绪因子 ====================

    def _score_leverage(self, df: pd.DataFrame) -> pd.Series:
        """
        杠杆情绪因子评分 (0-100)

        高分 = 乐观 (融资余额增长)
        低分 = 悲观 (融资余额萎缩)

        子因子:
        - 融资余额10日变化率百分位 (60%)
        - 融资/融券比率百分位 (40%)
        """
        scores = pd.Series(50.0, index=df.index)

        has_margin = 'margin_rzye' in df.columns

        if not has_margin:
            return scores

        # 1) 融资余额10日变化率百分位
        pct10_score = pd.Series(50.0, index=df.index)
        if 'margin_rzye_pct10' in df.columns:
            pct10_score = self._rolling_percentile(df['margin_rzye_pct10'])

        # 2) 融资/融券比率百分位
        ratio_score = pd.Series(50.0, index=df.index)
        if 'margin_rz_rq_ratio' in df.columns:
            ratio_score = self._rolling_percentile(df['margin_rz_rq_ratio'])

        scores = pct10_score * 0.60 + ratio_score * 0.40
        return scores.clip(0, 100)

    # ==================== 汇率因子 ====================

    def _score_fx(self, df: pd.DataFrame) -> pd.Series:
        """
        汇率因子评分 (0-100)

        高分 = 利好 (人民币升值, USDCNH下降)
        低分 = 利空 (人民币贬值, USDCNH上升)

        子因子:
        - USDCNH 水平百分位 (反向) (40%)
        - USDCNH 10日变化率 (反向) (35%)
        - USDCNH vs 20日均线位置 (反向) (25%)
        """
        scores = pd.Series(50.0, index=df.index)

        has_fx = 'fx_usdcnh' in df.columns

        if not has_fx:
            return scores

        # 1) 汇率水平百分位 (反向: 低汇率=人民币强=高分)
        fx_level = self._rolling_percentile(df['fx_usdcnh'])
        fx_level_score = 100 - fx_level

        # 2) 10日变化率 (反向: 贬值=低分)
        chg10_score = pd.Series(50.0, index=df.index)
        if 'fx_usdcnh_chg10' in df.columns:
            chg = df['fx_usdcnh_chg10']
            # 范围约 [-2%, +2%], 映射到 [0, 100]
            chg10_score = 50 - chg.clip(-2, 2) * 25  # 贬值(正)=低分
            chg10_score = chg10_score.fillna(50).clip(0, 100)

        # 3) vs 20日均线位置 (反向)
        ma_score = pd.Series(50.0, index=df.index)
        if 'fx_usdcnh_ma20' in df.columns:
            ma20 = df['fx_usdcnh_ma20']
            fx = df['fx_usdcnh']
            # 高于均线=贬值趋势=低分, 低于均线=升值趋势=高分
            ratio = ((fx / ma20.replace(0, np.nan)) - 1.0).clip(-0.02, 0.02)
            ma_score = 50 - ratio * 2500  # [-0.02, 0.02] -> [100, 0]
            ma_score = ma_score.fillna(50).clip(0, 100)

        scores = fx_level_score * 0.40 + chg10_score * 0.35 + ma_score * 0.25
        return scores.clip(0, 100)

    # ==================== 工具方法 ====================

    def _rolling_percentile(self, series: pd.Series) -> pd.Series:
        """
        计算滚动百分位 (0-100)

        使用 lookback_window 窗口内的排名百分位
        """
        window = self.lookback_window

        def pctl(x):
            if len(x) < 10:
                return 50.0
            return pd.Series(x).rank(pct=True).iloc[-1] * 100

        result = series.rolling(window, min_periods=20).apply(pctl, raw=False)
        return result.fillna(50.0).clip(0, 100)
