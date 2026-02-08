"""
通用偏离率计算器

计算收盘价相对于各均线的偏离率
支持：指数数据、基金数据、股票日线数据
"""

import json
from typing import List, Optional

import pandas as pd


class DeviationRateCalculator:
    """
    通用偏离率计算器
    
    计算公式：(close - ma_N) / ma_N
    
    使用示例:
        # 指数数据
        dev_calc = DeviationRateCalculator(ma_periods=[5,10,20,50])
        index_df = dev_calc.calculate(index_df)
        
        # 基金数据
        dev_calc = DeviationRateCalculator(ma_periods=[5,10,20,60,120])
        fund_df = dev_calc.calculate(fund_df)
    """
    
    DEFAULT_MA_PERIODS = [5, 10, 20, 50]
    
    def __init__(self,
                 ma_periods: Optional[List[int]] = None,
                 price_col: str = 'close',
                 output_as_json: bool = True,
                 output_col: str = 'deviation_rate',
                 decimal_places: int = 4):
        """
        初始化偏离率计算器
        
        Args:
            ma_periods: 要计算偏离率的均线周期，如 [5, 10, 20, 50]
            price_col: 价格列名，默认 'close'
            output_as_json: True=输出 JSON 字符串，False=输出多列
            output_col: 输出列名（仅当 output_as_json=True 时使用）
            decimal_places: 小数位数，默认 4
        """
        self.ma_periods = ma_periods or self.DEFAULT_MA_PERIODS
        self.price_col = price_col
        self.output_as_json = output_as_json
        self.output_col = output_col
        self.decimal_places = decimal_places
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算偏离率
        
        Args:
            df: 包含 close 和 ma_N 列的 DataFrame
                必须先调用 TechnicalIndicatorCalculator 计算均线
        
        Returns:
            pd.DataFrame: 添加 deviation_rate 列（JSON 或多列）的 DataFrame
        """
        result_df = df.copy()
        
        if self.output_as_json:
            result_df[self.output_col] = result_df.apply(
                lambda row: self._compute_deviation_json(row), axis=1
            )
        else:
            for period in self.ma_periods:
                ma_col = f'ma_{period}'
                dev_col = f'deviation_ma_{period}'
                if ma_col in result_df.columns:
                    result_df[dev_col] = result_df.apply(
                        lambda row: self._compute_single_deviation(row, ma_col), axis=1
                    )
        
        return result_df
    
    def _compute_deviation_json(self, row: pd.Series) -> str:
        """
        计算单行的偏离率并生成 JSON 字符串
        
        Args:
            row: DataFrame 的一行
        
        Returns:
            str: JSON 格式的偏离率
        """
        deviation_dict = {}
        close = row.get(self.price_col)
        
        if pd.isna(close) or close == 0:
            return json.dumps({})
        
        for period in self.ma_periods:
            ma_col = f'ma_{period}'
            ma_value = row.get(ma_col)
            
            if pd.notna(ma_value) and ma_value != 0:
                deviation = (close - ma_value) / ma_value
                deviation_dict[ma_col] = round(deviation, self.decimal_places)
            else:
                deviation_dict[ma_col] = None
        
        return json.dumps(deviation_dict)
    
    def _compute_single_deviation(self, row: pd.Series, ma_col: str) -> Optional[float]:
        """
        计算单个均线的偏离率
        
        Args:
            row: DataFrame 的一行
            ma_col: 均线列名
        
        Returns:
            float: 偏离率，如果无法计算则返回 None
        """
        close = row.get(self.price_col)
        ma_value = row.get(ma_col)
        
        if pd.isna(close) or pd.isna(ma_value) or ma_value == 0:
            return None
        
        deviation = (close - ma_value) / ma_value
        return round(deviation, self.decimal_places)
    
    @staticmethod
    def parse_deviation_json(json_str: str) -> dict:
        """
        解析偏离率 JSON 字符串
        
        Args:
            json_str: JSON 格式的偏离率字符串
        
        Returns:
            dict: 偏离率字典
        """
        if not json_str:
            return {}
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return {}
