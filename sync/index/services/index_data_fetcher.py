"""
指数数据获取服务

从 Tushare API 批量获取指数行情数据
"""

import time
from typing import List, Optional

import pandas as pd

from tu_share_factory.tu_share_factory import TuShareFactory
from util.date_util import TimeUtils


class IndexDataFetcher:
    """
    指数数据获取服务
    
    职责：
    - 从 Tushare API 批量获取指数行情数据
    - 获取交易日历过滤非交易日
    - 处理 API 限流
    """
    
    INDEX_FIELDS = [
        "ts_code", "trade_date", "open", "high", "low", "close",
        "pre_close", "change", "pct_chg", "vol", "amount"
    ]
    
    TRADE_CAL_FIELDS = [
        "exchange", "cal_date", "is_open", "pretrade_date"
    ]
    
    def __init__(self, api_sleep: float = 0.3, lookback_days: int = 100):
        """
        初始化数据获取服务
        
        Args:
            api_sleep: API 调用间隔时间（秒），用于限流
            lookback_days: 获取历史数据的回溯天数（用于计算技术指标）
        """
        self.api_sleep = api_sleep
        self.lookback_days = lookback_days
        self._pro = None
    
    @property
    def pro(self):
        """懒加载 Tushare API 客户端"""
        if self._pro is None:
            self._pro = TuShareFactory.build_api_client()
        return self._pro
    
    def fetch_index_daily(self, ts_code: str, start_date: str, end_date: str,
                         include_history: bool = True) -> pd.DataFrame:
        """
        获取指数日线行情数据
        
        Args:
            ts_code: 指数代码，如 '000300.SH'
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD
            include_history: 是否包含历史数据（用于计算技术指标）
        
        Returns:
            pd.DataFrame: 指数行情数据
        """
        # 如果需要计算技术指标，提前获取更多历史数据
        if include_history:
            fetch_start_date = TimeUtils.get_n_days_before_or_after(
                start_date, self.lookback_days, is_before=True
            )
        else:
            fetch_start_date = start_date
        
        time.sleep(self.api_sleep)
        
        try:
            daily_df = self.pro.index_daily(
                ts_code=ts_code,
                start_date=fetch_start_date,
                end_date=end_date,
                fields=self.INDEX_FIELDS
            )
            
            if daily_df.empty:
                return pd.DataFrame()
            
            # 按日期排序
            daily_df = daily_df.sort_values('trade_date').reset_index(drop=True)
            
            return daily_df
            
        except Exception as e:
            print(f"获取指数 {ts_code} 行情数据失败: {e}")
            return pd.DataFrame()
    
    def get_trading_days(self, exchange: str, start_date: str, end_date: str) -> List[str]:
        """
        获取交易日列表
        
        Args:
            exchange: 交易所代码，'SSE' 或 'SZSE'
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD
        
        Returns:
            List[str]: 交易日列表
        """
        time.sleep(self.api_sleep)
        
        try:
            trade_cal = self.pro.trade_cal(
                exchange=exchange,
                start_date=start_date,
                end_date=end_date,
                fields=self.TRADE_CAL_FIELDS
            )
            
            # 过滤开市日
            trading_days = trade_cal[trade_cal['is_open'] == 1]['cal_date'].tolist()
            return sorted(trading_days)
            
        except Exception as e:
            print(f"获取交易日历失败: {e}")
            return []
    
    def filter_trading_days(self, df: pd.DataFrame, ts_code: str,
                           start_date: str, end_date: str) -> pd.DataFrame:
        """
        过滤 DataFrame，只保留交易日数据
        
        Args:
            df: 包含 trade_date 列的 DataFrame
            ts_code: 指数代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            pd.DataFrame: 过滤后的 DataFrame
        """
        exchange = "SZSE" if ts_code.endswith("SZ") else "SSE"
        trading_days = self.get_trading_days(exchange, start_date, end_date)
        
        if not trading_days:
            return df
        
        return df[df['trade_date'].isin(trading_days)].reset_index(drop=True)
    
    def get_exchange(self, ts_code: str) -> str:
        """
        根据指数代码获取交易所
        
        Args:
            ts_code: 指数代码
        
        Returns:
            str: 交易所代码
        """
        return "SZSE" if ts_code.endswith("SZ") else "SSE"
