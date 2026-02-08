"""
历史百分位计算器

计算各项指标在历史数据中的百分位排名
支持偏离率、成交量、MACD、RSI、估值等指标
"""

import json
from typing import List, Optional

import pandas as pd
import numpy as np


class PercentileCalculator:
    """
    历史百分位计算器
    
    计算各类指标在历史数据中的百分位排名（0-100）
    
    使用示例:
        calc = PercentileCalculator(lookback_years=5)
        df = calc.calculate(df)
        # df 会新增 percentile_ranks 列（JSON格式）
    """
    
    # 默认计算的指标
    DEFAULT_INDICATORS = [
        'amount', 'vol',                          # 成交量
        'macd', 'macd_histogram',                 # MACD
        'rsi',                                     # RSI
        'pe_ttm', 'pb'                            # 估值
    ]
    
    # 偏离率指标（需要从JSON中解析）
    DEVIATION_INDICATORS = ['ma_5', 'ma_10', 'ma_20', 'ma_50']
    
    def __init__(self,
                 lookback_years: int = 5,
                 indicators: Optional[List[str]] = None,
                 include_deviation: bool = True,
                 output_col: str = 'percentile_ranks',
                 decimal_places: int = 2):
        """
        初始化历史百分位计算器
        
        Args:
            lookback_years: 回溯年数，默认5年（约1250个交易日）
            indicators: 要计算的指标列表
            include_deviation: 是否包含偏离率百分位
            output_col: 输出列名
            decimal_places: 小数位数
        """
        self.lookback_years = lookback_years
        self.lookback_days = lookback_years * 250  # 每年约250个交易日
        self.indicators = indicators or self.DEFAULT_INDICATORS
        self.include_deviation = include_deviation
        self.output_col = output_col
        self.decimal_places = decimal_places
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有指标的历史百分位
        
        Args:
            df: 包含指标数据的DataFrame
        
        Returns:
            pd.DataFrame: 添加 percentile_ranks 列的 DataFrame
        """
        result_df = df.copy()
        
        # 计算各指标的百分位
        percentile_data = {}
        
        # 基础指标
        for indicator in self.indicators:
            if indicator in result_df.columns:
                percentile_data[indicator] = self._calculate_rolling_percentile(
                    result_df[indicator]
                )
        
        # 偏离率指标（需要从JSON解析）
        if self.include_deviation and 'deviation_rate' in result_df.columns:
            deviation_percentiles = self._calculate_deviation_percentiles(result_df)
            percentile_data.update(deviation_percentiles)
        
        # 合并为JSON
        result_df[self.output_col] = result_df.apply(
            lambda row: self._build_percentile_json(row, percentile_data),
            axis=1
        )
        
        return result_df
    
    def _calculate_rolling_percentile(self, series: pd.Series) -> pd.Series:
        """
        计算滚动窗口百分位
        
        使用历史数据（最多lookback_days天）计算当前值的百分位排名
        
        Args:
            series: 数据序列
        
        Returns:
            pd.Series: 百分位排名序列（0-100）
        """
        def calc_percentile(window):
            if len(window) < 2:
                return np.nan
            current_value = window.iloc[-1]
            if pd.isna(current_value):
                return np.nan
            # 计算当前值在窗口中的百分位排名
            count_below = (window < current_value).sum()
            count_equal = (window == current_value).sum()
            # 使用平均排名法
            percentile = (count_below + count_equal / 2) / len(window) * 100
            return round(percentile, self.decimal_places)
        
        # 使用扩展窗口，最大为lookback_days
        percentiles = []
        for i in range(len(series)):
            start_idx = max(0, i - self.lookback_days + 1)
            window = series.iloc[start_idx:i+1]
            percentiles.append(calc_percentile(window))
        
        return pd.Series(percentiles, index=series.index)
    
    def _calculate_deviation_percentiles(self, df: pd.DataFrame) -> dict:
        """
        计算偏离率的百分位
        
        从deviation_rate JSON列中解析偏离率，并计算各均线偏离率的百分位
        
        Args:
            df: DataFrame
        
        Returns:
            dict: 各偏离率指标的百分位序列
        """
        result = {}
        
        # 先将JSON解析为多列
        deviation_data = {}
        for indicator in self.DEVIATION_INDICATORS:
            deviation_data[indicator] = []
        
        for _, row in df.iterrows():
            deviation_str = row.get('deviation_rate', '')
            try:
                deviation_dict = json.loads(deviation_str) if deviation_str else {}
            except (json.JSONDecodeError, TypeError):
                deviation_dict = {}
            
            for indicator in self.DEVIATION_INDICATORS:
                value = deviation_dict.get(indicator)
                deviation_data[indicator].append(value)
        
        # 计算每个偏离率指标的百分位
        for indicator in self.DEVIATION_INDICATORS:
            series = pd.Series(deviation_data[indicator], index=df.index)
            # 转换为float，处理None值
            series = pd.to_numeric(series, errors='coerce')
            key = f'deviation_{indicator}'
            result[key] = self._calculate_rolling_percentile(series)
        
        return result
    
    def _build_percentile_json(self, row: pd.Series, percentile_data: dict) -> str:
        """
        构建百分位JSON字符串
        
        Args:
            row: DataFrame的一行
            percentile_data: 各指标百分位数据字典
        
        Returns:
            str: JSON格式的百分位字符串
        """
        idx = row.name
        percentile_dict = {}
        
        for key, series in percentile_data.items():
            if idx in series.index:
                value = series.loc[idx]
                if pd.notna(value):
                    percentile_dict[key] = round(float(value), self.decimal_places)
                else:
                    percentile_dict[key] = None
            else:
                percentile_dict[key] = None
        
        return json.dumps(percentile_dict)
    
    @staticmethod
    def parse_percentile_json(json_str: str) -> dict:
        """
        解析百分位JSON字符串
        
        Args:
            json_str: JSON格式的百分位字符串
        
        Returns:
            dict: 百分位字典
        """
        if not json_str:
            return {}
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @staticmethod
    def get_percentile_level(percentile: float) -> str:
        """
        获取百分位级别描述
        
        Args:
            percentile: 百分位值（0-100）
        
        Returns:
            str: 级别描述
        """
        if percentile is None:
            return '未知'
        if percentile >= 90:
            return '极高'
        elif percentile >= 80:
            return '高位'
        elif percentile >= 60:
            return '中高'
        elif percentile >= 40:
            return '中位'
        elif percentile >= 20:
            return '中低'
        elif percentile >= 10:
            return '低位'
        else:
            return '极低'
    
    @staticmethod
    def get_percentile_color(percentile: float) -> str:
        """
        获取百分位对应的颜色
        
        Args:
            percentile: 百分位值（0-100）
        
        Returns:
            str: 颜色名称
        """
        if percentile is None:
            return 'gray'
        if percentile >= 80:
            return 'darkred'      # 高位警示
        elif percentile >= 60:
            return 'orange'
        elif percentile >= 40:
            return 'gray'         # 中性
        elif percentile >= 20:
            return 'lightgreen'
        else:
            return 'darkgreen'    # 低位机会
