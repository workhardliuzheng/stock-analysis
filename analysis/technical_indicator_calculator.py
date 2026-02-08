"""
通用技术指标计算器

支持：指数数据、基金数据、股票日线数据
使用 TA-Lib 库进行技术指标计算
"""

from typing import List, Optional

import numpy as np
import pandas as pd
import talib


class TechnicalIndicatorCalculator:
    """
    通用技术指标计算器
    
    支持计算：
    - MA (移动平均线)
    - WMA (加权移动平均线)
    - MACD
    - RSI
    - KDJ
    - 布林带
    - OBV
    
    使用示例:
        # 指数数据：完整技术指标
        calc = TechnicalIndicatorCalculator(ma_periods=[5,10,20,50])
        index_df = calc.calculate(index_df)
        
        # 基金数据：仅需 MA 指标
        calc = TechnicalIndicatorCalculator(
            ma_periods=[5,10,20,60,120],
            include_macd=False,
            include_kdj=False,
            include_bollinger=False
        )
        fund_df = calc.calculate(fund_df)
    """
    
    DEFAULT_MA_PERIODS = [5, 10, 20, 50]
    DEFAULT_WMA_PERIODS = [5, 10, 20, 50]
    
    def __init__(self,
                 ma_periods: Optional[List[int]] = None,
                 wma_periods: Optional[List[int]] = None,
                 include_wma: bool = True,
                 include_macd: bool = True,
                 include_kdj: bool = True,
                 include_bollinger: bool = True,
                 include_rsi: bool = True,
                 include_obv: bool = True,
                 price_col: str = 'close',
                 date_col: str = 'trade_date',
                 macd_config: Optional[dict] = None,
                 kdj_config: Optional[dict] = None,
                 bollinger_config: Optional[dict] = None,
                 rsi_period: int = 14):
        """
        初始化技术指标计算器
        
        Args:
            ma_periods: MA 周期列表，如 [5, 10, 20, 50]
            wma_periods: WMA 周期列表，如 [5, 10, 20, 50]
            include_wma: 是否计算 WMA
            include_macd: 是否计算 MACD
            include_kdj: 是否计算 KDJ
            include_bollinger: 是否计算布林带
            include_rsi: 是否计算 RSI
            include_obv: 是否计算 OBV
            price_col: 价格列名，默认 'close'
            date_col: 日期列名，默认 'trade_date'
            macd_config: MACD 配置，默认 {'fast': 12, 'slow': 26, 'signal': 9}
            kdj_config: KDJ 配置，默认 {'fastk': 9, 'slowk': 3, 'slowd': 3}
            bollinger_config: 布林带配置，默认 {'period': 20, 'nbdev': 2}
            rsi_period: RSI 周期，默认 14
        """
        self.ma_periods = ma_periods or self.DEFAULT_MA_PERIODS
        self.wma_periods = wma_periods or self.DEFAULT_WMA_PERIODS
        self.include_wma = include_wma
        self.include_macd = include_macd
        self.include_kdj = include_kdj
        self.include_bollinger = include_bollinger
        self.include_rsi = include_rsi
        self.include_obv = include_obv
        self.price_col = price_col
        self.date_col = date_col
        self.rsi_period = rsi_period
        
        # 默认配置
        self.macd_config = macd_config or {'fast': 12, 'slow': 26, 'signal': 9}
        self.kdj_config = kdj_config or {'fastk': 9, 'slowk': 3, 'slowd': 3}
        self.bollinger_config = bollinger_config or {'period': 20, 'nbdev': 2}
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有配置的技术指标
        
        Args:
            df: 包含 OHLCV 数据的 DataFrame
                必须包含列: close (或 price_col 指定的列)
                可选列: high, low, open, vol (用于特定指标)
        
        Returns:
            pd.DataFrame: 添加了技术指标列的 DataFrame
        """
        # 确保数据按日期排序
        if self.date_col in df.columns:
            df = df.sort_values(self.date_col).reset_index(drop=True)
        
        # 复制数据以避免修改原始数据
        result_df = df.copy()
        
        # 转换为 numpy 数组供 TA-Lib 使用
        close = result_df[self.price_col].values.astype(float)
        
        # 计算 MA
        result_df = self._calculate_ma(result_df, close)
        
        # 计算 WMA
        if self.include_wma:
            result_df = self._calculate_wma(result_df, close)
        
        # 计算 MACD
        if self.include_macd:
            result_df = self._calculate_macd(result_df, close)
        
        # 计算 RSI
        if self.include_rsi:
            result_df = self._calculate_rsi(result_df, close)
        
        # 计算 KDJ (需要 high, low)
        if self.include_kdj and 'high' in result_df.columns and 'low' in result_df.columns:
            result_df = self._calculate_kdj(result_df)
        
        # 计算布林带
        if self.include_bollinger:
            result_df = self._calculate_bollinger(result_df, close)
        
        # 计算 OBV (需要 vol)
        if self.include_obv and 'vol' in result_df.columns:
            result_df = self._calculate_obv(result_df, close)
        
        return result_df
    
    def calculate_ma_only(self, df: pd.DataFrame, periods: Optional[List[int]] = None) -> pd.DataFrame:
        """
        仅计算移动平均线（兼容简单场景）
        
        Args:
            df: 包含价格数据的 DataFrame
            periods: MA 周期列表，默认使用初始化时的配置
        
        Returns:
            pd.DataFrame: 添加了 MA 列的 DataFrame
        """
        periods = periods or self.ma_periods
        
        if self.date_col in df.columns:
            df = df.sort_values(self.date_col).reset_index(drop=True)
        
        result_df = df.copy()
        close = result_df[self.price_col].values.astype(float)
        
        for period in periods:
            col_name = f'ma_{period}'
            result_df[col_name] = talib.SMA(close, timeperiod=period)
        
        return result_df
    
    def _calculate_ma(self, df: pd.DataFrame, close: np.ndarray) -> pd.DataFrame:
        """计算移动平均线"""
        for period in self.ma_periods:
            col_name = f'ma_{period}'
            df[col_name] = talib.SMA(close, timeperiod=period)
        return df
    
    def _calculate_wma(self, df: pd.DataFrame, close: np.ndarray) -> pd.DataFrame:
        """计算加权移动平均线"""
        for period in self.wma_periods:
            col_name = f'wma_{period}'
            df[col_name] = talib.WMA(close, timeperiod=period)
        return df
    
    def _calculate_macd(self, df: pd.DataFrame, close: np.ndarray) -> pd.DataFrame:
        """计算 MACD 指标"""
        macd, macd_signal, macd_hist = talib.MACD(
            close,
            fastperiod=self.macd_config['fast'],
            slowperiod=self.macd_config['slow'],
            signalperiod=self.macd_config['signal']
        )
        df['macd'] = macd
        df['macd_signal_line'] = macd_signal
        df['macd_histogram'] = macd_hist
        return df
    
    def _calculate_rsi(self, df: pd.DataFrame, close: np.ndarray) -> pd.DataFrame:
        """计算 RSI 指标"""
        df['rsi'] = talib.RSI(close, timeperiod=self.rsi_period)
        return df
    
    def _calculate_kdj(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算 KDJ 指标"""
        high = df['high'].values.astype(float)
        low = df['low'].values.astype(float)
        close = df[self.price_col].values.astype(float)
        
        slowk, slowd = talib.STOCH(
            high, low, close,
            fastk_period=self.kdj_config['fastk'],
            slowk_period=self.kdj_config['slowk'],
            slowk_matype=0,
            slowd_period=self.kdj_config['slowd'],
            slowd_matype=0
        )
        df['kdj_k'] = slowk
        df['kdj_d'] = slowd
        df['kdj_j'] = 3 * slowk - 2 * slowd  # J = 3K - 2D
        return df
    
    def _calculate_bollinger(self, df: pd.DataFrame, close: np.ndarray) -> pd.DataFrame:
        """计算布林带"""
        bb_upper, bb_middle, bb_lower = talib.BBANDS(
            close,
            timeperiod=self.bollinger_config['period'],
            nbdevup=self.bollinger_config['nbdev'],
            nbdevdn=self.bollinger_config['nbdev'],
            matype=0
        )
        df['bb_high'] = bb_upper
        df['bb_mid'] = bb_middle
        df['bb_low'] = bb_lower
        return df
    
    def _calculate_obv(self, df: pd.DataFrame, close: np.ndarray) -> pd.DataFrame:
        """计算 OBV 指标"""
        volume = df['vol'].values.astype(float)
        df['obv'] = talib.OBV(close, volume)
        return df
