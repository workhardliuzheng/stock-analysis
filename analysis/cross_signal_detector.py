"""
交叉信号检测器

检测均线金叉死叉、MACD金叉死叉、MACD柱状图趋势变化
"""

import json
from typing import List, Tuple, Optional

import pandas as pd
import numpy as np


class CrossSignalDetector:
    """
    交叉信号检测器
    
    检测内容：
    1. 均线金叉死叉（MA5-MA10, MA10-MA20）
    2. MACD金叉死叉
    3. MACD柱状图趋势（红柱变长/变短，绿柱变长/变短）
    
    使用示例:
        detector = CrossSignalDetector()
        df = detector.detect(df)
        # df 会新增 cross_signals 列（JSON格式）
    """
    
    # 信号类型常量
    GOLDEN_CROSS = 'golden_cross'  # 金叉
    DEATH_CROSS = 'death_cross'    # 死叉
    RED_LONGER = 'red_longer'       # 红柱变长
    RED_SHORTER = 'red_shorter'     # 红柱变短
    GREEN_LONGER = 'green_longer'   # 绿柱变长
    GREEN_SHORTER = 'green_shorter' # 绿柱变短
    
    DEFAULT_MA_CROSS_PAIRS = [(5, 10), (10, 20)]
    
    def __init__(self,
                 ma_cross_pairs: Optional[List[Tuple[int, int]]] = None,
                 output_col: str = 'cross_signals'):
        """
        初始化交叉信号检测器
        
        Args:
            ma_cross_pairs: 均线交叉检测对，如 [(5, 10), (10, 20)]
            output_col: 输出列名
        """
        self.ma_cross_pairs = ma_cross_pairs or self.DEFAULT_MA_CROSS_PAIRS
        self.output_col = output_col
    
    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        检测所有交叉信号
        
        Args:
            df: 包含均线和MACD列的DataFrame
                必须包含: ma_5, ma_10, ma_20, macd, macd_signal_line, macd_histogram
        
        Returns:
            pd.DataFrame: 添加 cross_signals 列的 DataFrame
        """
        result_df = df.copy()
        
        # 检测各项信号
        ma_signals = {}
        for short_period, long_period in self.ma_cross_pairs:
            key = f'ma_{short_period}_{long_period}'
            ma_signals[key] = self._detect_ma_cross(result_df, short_period, long_period)
        
        macd_cross = self._detect_macd_cross(result_df)
        macd_trend = self._analyze_macd_histogram_trend(result_df)
        
        # 合并为JSON
        result_df[self.output_col] = result_df.apply(
            lambda row: self._build_signal_json(row, ma_signals, macd_cross, macd_trend),
            axis=1
        )
        
        return result_df
    
    def _detect_ma_cross(self, df: pd.DataFrame, short_period: int, long_period: int) -> pd.Series:
        """
        检测均线金叉死叉
        
        金叉：前日短期均线 < 长期均线，今日短期均线 > 长期均线
        死叉：前日短期均线 > 长期均线，今日短期均线 < 长期均线
        
        Args:
            df: DataFrame
            short_period: 短期均线周期
            long_period: 长期均线周期
        
        Returns:
            pd.Series: 交叉信号序列
        """
        short_col = f'ma_{short_period}'
        long_col = f'ma_{long_period}'
        
        if short_col not in df.columns or long_col not in df.columns:
            return pd.Series([None] * len(df), index=df.index)
        
        short_ma = df[short_col]
        long_ma = df[long_col]
        
        # 计算差值
        diff = short_ma - long_ma
        prev_diff = diff.shift(1)
        
        # 金叉：前日 diff < 0，今日 diff > 0
        golden_cross = (prev_diff < 0) & (diff > 0)
        # 死叉：前日 diff > 0，今日 diff < 0
        death_cross = (prev_diff > 0) & (diff < 0)
        
        signals = pd.Series([None] * len(df), index=df.index)
        signals[golden_cross] = self.GOLDEN_CROSS
        signals[death_cross] = self.DEATH_CROSS
        
        return signals
    
    def _detect_macd_cross(self, df: pd.DataFrame) -> pd.Series:
        """
        检测MACD金叉死叉
        
        金叉：前日 MACD < 信号线，今日 MACD > 信号线
        死叉：前日 MACD > 信号线，今日 MACD < 信号线
        
        Args:
            df: DataFrame
        
        Returns:
            pd.Series: MACD交叉信号序列
        """
        if 'macd' not in df.columns or 'macd_signal_line' not in df.columns:
            return pd.Series([None] * len(df), index=df.index)
        
        macd = df['macd']
        signal = df['macd_signal_line']
        
        diff = macd - signal
        prev_diff = diff.shift(1)
        
        golden_cross = (prev_diff < 0) & (diff > 0)
        death_cross = (prev_diff > 0) & (diff < 0)
        
        signals = pd.Series([None] * len(df), index=df.index)
        signals[golden_cross] = self.GOLDEN_CROSS
        signals[death_cross] = self.DEATH_CROSS
        
        return signals
    
    def _analyze_macd_histogram_trend(self, df: pd.DataFrame) -> pd.Series:
        """
        分析MACD柱状图趋势变化
        
        红柱变长：连续正值且数值增大
        红柱变短：连续正值且数值减小
        绿柱变长：连续负值且绝对值增大
        绿柱变短：连续负值且绝对值减小
        
        Args:
            df: DataFrame
        
        Returns:
            pd.Series: 柱状图趋势信号序列
        """
        if 'macd_histogram' not in df.columns:
            return pd.Series([None] * len(df), index=df.index)
        
        hist = df['macd_histogram']
        prev_hist = hist.shift(1)
        
        # 当前是红柱（正值）
        is_red = hist > 0
        prev_is_red = prev_hist > 0
        
        # 当前是绿柱（负值）
        is_green = hist < 0
        prev_is_green = prev_hist < 0
        
        # 红柱变长：当前和前一日都是红柱，且当前值更大
        red_longer = is_red & prev_is_red & (hist > prev_hist)
        # 红柱变短：当前和前一日都是红柱，且当前值更小
        red_shorter = is_red & prev_is_red & (hist < prev_hist)
        
        # 绿柱变长：当前和前一日都是绿柱，且当前绝对值更大（值更小）
        green_longer = is_green & prev_is_green & (hist < prev_hist)
        # 绿柱变短：当前和前一日都是绿柱，且当前绝对值更小（值更大）
        green_shorter = is_green & prev_is_green & (hist > prev_hist)
        
        signals = pd.Series([None] * len(df), index=df.index)
        signals[red_longer] = self.RED_LONGER
        signals[red_shorter] = self.RED_SHORTER
        signals[green_longer] = self.GREEN_LONGER
        signals[green_shorter] = self.GREEN_SHORTER
        
        return signals
    
    def _build_signal_json(self, row: pd.Series, 
                           ma_signals: dict, 
                           macd_cross: pd.Series, 
                           macd_trend: pd.Series) -> str:
        """
        构建信号JSON字符串
        
        Args:
            row: DataFrame的一行
            ma_signals: 均线交叉信号字典
            macd_cross: MACD交叉信号序列
            macd_trend: MACD趋势信号序列
        
        Returns:
            str: JSON格式的信号字符串
        """
        idx = row.name
        signal_dict = {}
        
        # 添加均线交叉信号
        for key, signals in ma_signals.items():
            signal_dict[key] = signals.loc[idx] if idx in signals.index else None
        
        # 添加MACD交叉信号
        signal_dict['macd'] = macd_cross.loc[idx] if idx in macd_cross.index else None
        
        # 添加MACD柱状图趋势
        signal_dict['macd_hist_trend'] = macd_trend.loc[idx] if idx in macd_trend.index else None
        
        return json.dumps(signal_dict)
    
    @staticmethod
    def parse_signal_json(json_str: str) -> dict:
        """
        解析信号JSON字符串
        
        Args:
            json_str: JSON格式的信号字符串
        
        Returns:
            dict: 信号字典
        """
        if not json_str:
            return {}
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def find_latest_cross_date(self, df: pd.DataFrame, signal_type: str, 
                                cross_key: str = 'ma_5_10') -> Optional[Tuple[str, int]]:
        """
        查找最近一次交叉的日期和距今天数
        
        Args:
            df: 包含cross_signals列的DataFrame
            signal_type: 信号类型（'golden_cross' 或 'death_cross'）
            cross_key: 交叉类型键名
        
        Returns:
            Tuple[str, int]: (交叉日期, 距今天数) 或 None
        """
        if self.output_col not in df.columns:
            return None
        
        for i in range(len(df) - 1, -1, -1):
            row = df.iloc[i]
            signals = self.parse_signal_json(row.get(self.output_col, ''))
            if signals.get(cross_key) == signal_type:
                trade_date = row.get('trade_date', '')
                days_ago = len(df) - 1 - i
                return (trade_date, days_ago)
        
        return None
