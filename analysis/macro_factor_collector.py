"""
V13 宏观因子数据采集器

从 Tushare Pro API 获取宏观经济数据，按交易日对齐后供下游模块使用。

数据源 (4类):
1. Shibor 利率 (隔夜/1周/1月) - 反映资金面松紧
2. 北向资金 (沪股通+深股通净买入) - 外资风向标
3. 融资融券余额 - 杠杆资金情绪指标
4. 人民币汇率 (USDCNH) - 影响资金流向

设计原则:
1. 内存缓存: 同一进程内只获取一次，避免重复API调用
2. 容错降级: 任何数据源不可用时跳过，不影响其他源
3. 前向填充: 非交易日/缺失数据用最近有效值填充
4. 无未来泄露: 所有特征仅使用当天及之前数据
"""

import os
import sys
from typing import Optional, Dict

import numpy as np
import pandas as pd

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


class MacroFactorCollector:
    """
    宏观因子数据采集器

    使用示例:
        collector = MacroFactorCollector()
        macro_df = collector.collect('20180101', '20260418')
        # macro_df 包含 trade_date + 各宏观指标列
    """

    # 内存缓存 (类变量，进程级别共享)
    _cache: Optional[pd.DataFrame] = None
    _cache_start: Optional[str] = None
    _cache_end: Optional[str] = None

    # Shibor 期限
    SHIBOR_TERMS = ['on', '1w', '1m']  # 隔夜, 1周, 1月

    def __init__(self):
        self._pro = None

    def _get_api(self):
        """延迟获取 Tushare API 客户端"""
        if self._pro is None:
            from tu_share_factory.tu_share_factory import TuShareFactory
            self._pro = TuShareFactory.build_api_client()
        return self._pro

    def collect(self, start_date: str, end_date: str,
                force_refresh: bool = False) -> pd.DataFrame:
        """
        采集宏观因子数据

        Args:
            start_date: 起始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            force_refresh: 强制刷新缓存

        Returns:
            DataFrame: 包含 trade_date + 宏观指标列，按 trade_date 升序排列
        """
        # 检查缓存
        if not force_refresh and self._is_cached(start_date, end_date):
            return self._filter_cache(start_date, end_date)

        print(f"  [V16] 采集宏观因子数据 ({start_date} ~ {end_date})...")

        all_data = {}

        # 1. Shibor 利率
        shibor_df = self._fetch_shibor(start_date, end_date)
        if shibor_df is not None:
            all_data['shibor'] = shibor_df

        # 2. 北向资金
        north_df = self._fetch_north_flow(start_date, end_date)
        if north_df is not None:
            all_data['north'] = north_df

        # 3. 融资融券
        margin_df = self._fetch_margin(start_date, end_date)
        if margin_df is not None:
            all_data['margin'] = margin_df

        # 4. 汇率 (美元/人民币)
        fx_df = self._fetch_fx(start_date, end_date)
        if fx_df is not None:
            all_data['fx'] = fx_df

        # 合并所有数据
        if not all_data:
            print("  [WARNING] 无宏观数据可用，返回空DataFrame")
            return pd.DataFrame(columns=['trade_date'])

        merged = None
        for name, df in all_data.items():
            if merged is None:
                merged = df
            else:
                merged = pd.merge(merged, df, on='trade_date', how='outer')

        merged = merged.sort_values('trade_date').reset_index(drop=True)

        # 前向填充缺失值
        fill_cols = [c for c in merged.columns if c != 'trade_date']
        merged[fill_cols] = merged[fill_cols].ffill()

        # 计算衍生指标 (变化率、滚动均值等)
        merged = self._compute_derived_features(merged)

        # 更新缓存
        MacroFactorCollector._cache = merged
        MacroFactorCollector._cache_start = start_date
        MacroFactorCollector._cache_end = end_date

        n_sources = len(all_data)
        n_cols = len([c for c in merged.columns if c != 'trade_date'])
        print(f"  [V16] 宏观数据采集完成: {n_sources}个数据源, {n_cols}个指标, {len(merged)}行")

        return self._filter_cache(start_date, end_date)

    # ==================== 数据源采集 ====================

    def _fetch_shibor(self, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        获取 Shibor 利率数据

        Tushare API: pro.shibor(start_date, end_date)
        返回: 隔夜(on), 1周(1w), 1月(1m) 利率
        """
        try:
            pro = self._get_api()
            df = pro.shibor(start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                print("    Shibor: 无数据")
                return None

            result = pd.DataFrame()
            result['trade_date'] = pd.to_datetime(df['date'])
            result['shibor_on'] = pd.to_numeric(df['on'], errors='coerce')
            result['shibor_1w'] = pd.to_numeric(df['1w'], errors='coerce')
            result['shibor_1m'] = pd.to_numeric(df['1m'], errors='coerce')

            print(f"    Shibor: {len(result)}行")
            return result.sort_values('trade_date').reset_index(drop=True)

        except Exception as e:
            print(f"    Shibor: 获取失败 ({e})")
            return None

    def _fetch_north_flow(self, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        获取北向资金数据 (沪股通+深股通)

        Tushare API: pro.moneyflow_hsgt(start_date, end_date)
        关键字段:
        - north_money: 北向资金净买入额 (百万)
        - south_money: 南向资金净买入额 (百万)
        """
        try:
            pro = self._get_api()
            df = pro.moneyflow_hsgt(start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                print("    北向资金: 无数据")
                return None

            result = pd.DataFrame()
            result['trade_date'] = pd.to_datetime(df['trade_date'])
            result['north_money'] = pd.to_numeric(df['north_money'], errors='coerce')
            result['south_money'] = pd.to_numeric(df['south_money'], errors='coerce')

            # 沪股通/深股通分别
            if 'hgt' in df.columns:
                result['hgt'] = pd.to_numeric(df['hgt'], errors='coerce')
            if 'sgt' in df.columns:
                result['sgt'] = pd.to_numeric(df['sgt'], errors='coerce')

            print(f"    北向资金: {len(result)}行")
            return result.sort_values('trade_date').reset_index(drop=True)

        except Exception as e:
            print(f"    北向资金: 获取失败 ({e})")
            return None

    def _fetch_margin(self, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        获取融资融券余额数据

        Tushare API: pro.margin(start_date, end_date, exchange_id='')
        关键字段:
        - rzye: 融资余额 (元)
        - rqye: 融券余额 (元)
        """
        try:
            pro = self._get_api()
            # 获取沪市和深市合计
            df_sh = pro.margin(start_date=start_date, end_date=end_date,
                               exchange_id='SSE')
            df_sz = pro.margin(start_date=start_date, end_date=end_date,
                               exchange_id='SZSE')

            frames = []
            if df_sh is not None and not df_sh.empty:
                frames.append(df_sh)
            if df_sz is not None and not df_sz.empty:
                frames.append(df_sz)

            if not frames:
                print("    融资融券: 无数据")
                return None

            df = pd.concat(frames, ignore_index=True)
            df['trade_date'] = pd.to_datetime(df['trade_date'])

            # 按日期汇总 (沪+深)
            df['rzye'] = pd.to_numeric(df['rzye'], errors='coerce')
            df['rqye'] = pd.to_numeric(df['rqye'], errors='coerce')
            daily = df.groupby('trade_date').agg({
                'rzye': 'sum',
                'rqye': 'sum',
            }).reset_index()

            result = pd.DataFrame()
            result['trade_date'] = daily['trade_date']
            result['margin_rzye'] = daily['rzye']  # 融资余额
            result['margin_rqye'] = daily['rqye']  # 融券余额
            result['margin_total'] = daily['rzye'] + daily['rqye']  # 两融合计

            print(f"    融资融券: {len(result)}行")
            return result.sort_values('trade_date').reset_index(drop=True)

        except Exception as e:
            print(f"    融资融券: 获取失败 ({e})")
            return None

    def _fetch_fx(self, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        获取美元/人民币汇率

        Tushare API: pro.fx_daily(ts_code='USDCNH.FXCM', start_date, end_date)
        备选: pro.fx_obasic
        """
        try:
            pro = self._get_api()
            # 尝试获取离岸人民币汇率
            df = pro.fx_daily(ts_code='USDCNH.FXCM',
                              start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                # 备选: 尝试在岸人民币
                df = pro.fx_daily(ts_code='USDCNY.FXCM',
                                  start_date=start_date, end_date=end_date)

            if df is None or df.empty:
                print("    汇率: 无数据")
                return None

            result = pd.DataFrame()
            result['trade_date'] = pd.to_datetime(df['trade_date'])

            # fx_daily 收盘价列可能是 'close' 或 'bid_close' 或 'ask_close'
            close_col = None
            for col_name in ['close', 'bid_close', 'ask_close']:
                if col_name in df.columns:
                    close_col = col_name
                    break

            if close_col is None:
                print(f"    汇率: 无价格列 (可用列: {list(df.columns)})")
                return None

            result['fx_usdcnh'] = pd.to_numeric(df[close_col], errors='coerce')

            print(f"    汇率: {len(result)}行 (列={close_col})")
            return result.sort_values('trade_date').reset_index(drop=True)

        except Exception as e:
            print(f"    汇率: 获取失败 ({e})")
            return None

    # ==================== 衍生特征计算 ====================

    def _compute_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算衍生宏观特征

        所有特征仅使用当天及之前数据 (无未来泄露)
        """
        result = df.copy()

        # --- Shibor 衍生特征 ---
        if 'shibor_on' in result.columns:
            # 利率变化 (日变化, bp)
            result['shibor_on_chg'] = result['shibor_on'].diff()
            result['shibor_1w_chg'] = result['shibor_1w'].diff() if 'shibor_1w' in result.columns else np.nan
            result['shibor_1m_chg'] = result['shibor_1m'].diff() if 'shibor_1m' in result.columns else np.nan

            # 利率10日变化 (反映趋势)
            result['shibor_on_chg10'] = result['shibor_on'].diff(10)

            # 期限利差 (1m - on, 正常为正, 倒挂为异常信号)
            if 'shibor_1m' in result.columns:
                result['shibor_term_spread'] = result['shibor_1m'] - result['shibor_on']

            # 20日均值 (平滑)
            result['shibor_on_ma20'] = result['shibor_on'].rolling(20, min_periods=5).mean()

        # --- 北向资金衍生特征 ---
        if 'north_money' in result.columns:
            # 5日/10日/20日累计净买入
            result['north_money_5d'] = result['north_money'].rolling(5, min_periods=1).sum()
            result['north_money_10d'] = result['north_money'].rolling(10, min_periods=3).sum()
            result['north_money_20d'] = result['north_money'].rolling(20, min_periods=5).sum()

            # 20日均值 (平滑每日波动)
            result['north_money_ma20'] = result['north_money'].rolling(20, min_periods=5).mean()

        # --- 融资融券衍生特征 ---
        if 'margin_rzye' in result.columns:
            # 融资余额变化率 (%)
            result['margin_rzye_pct'] = result['margin_rzye'].pct_change() * 100
            # 10日变化率
            result['margin_rzye_pct10'] = result['margin_rzye'].pct_change(10) * 100
            # 20日均值
            result['margin_rzye_ma20'] = result['margin_rzye'].rolling(20, min_periods=5).mean()
            # 融资/融券比例 (高=乐观)
            result['margin_rz_rq_ratio'] = (
                result['margin_rzye'] / result['margin_rqye'].replace(0, np.nan)
            )

        # --- 汇率衍生特征 ---
        if 'fx_usdcnh' in result.columns:
            # 汇率变化 (人民币贬值=正, 升值=负)
            result['fx_usdcnh_chg'] = result['fx_usdcnh'].pct_change() * 100
            # 10日变化
            result['fx_usdcnh_chg10'] = result['fx_usdcnh'].pct_change(10) * 100
            # 20日均值
            result['fx_usdcnh_ma20'] = result['fx_usdcnh'].rolling(20, min_periods=5).mean()

        return result

    # ==================== 缓存管理 ====================

    def _is_cached(self, start_date: str, end_date: str) -> bool:
        """检查缓存是否覆盖请求的日期范围"""
        if MacroFactorCollector._cache is None:
            return False
        if MacroFactorCollector._cache_start is None:
            return False
        return (MacroFactorCollector._cache_start <= start_date and
                MacroFactorCollector._cache_end >= end_date)

    def _filter_cache(self, start_date: str, end_date: str) -> pd.DataFrame:
        """从缓存中过滤指定日期范围"""
        df = MacroFactorCollector._cache
        if df is None or df.empty:
            return pd.DataFrame(columns=['trade_date'])
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        mask = (df['trade_date'] >= start_dt) & (df['trade_date'] <= end_dt)
        return df[mask].copy().reset_index(drop=True)

    @classmethod
    def clear_cache(cls):
        """清除缓存 (测试用)"""
        cls._cache = None
        cls._cache_start = None
        cls._cache_end = None

    # ==================== 数据对齐 ====================

    @staticmethod
    def align_to_index(macro_df: pd.DataFrame,
                       index_df: pd.DataFrame) -> pd.DataFrame:
        """
        将宏观数据对齐到指数数据的交易日

        使用 merge_asof 进行前向匹配 (backward fill):
        宏观数据日期 <= 指数交易日期

        Args:
            macro_df: 宏观因子 DataFrame (含 trade_date)
            index_df: 指数数据 DataFrame (含 trade_date)

        Returns:
            DataFrame: index_df 合并宏观数据列后的结果
        """
        if macro_df.empty:
            return index_df

        # 确保日期类型并统一精度 (ns)
        macro = macro_df.copy()
        idx = index_df.copy()
        macro['trade_date'] = pd.to_datetime(macro['trade_date']).dt.as_unit('ns')
        idx['trade_date'] = pd.to_datetime(idx['trade_date']).dt.as_unit('ns')

        # 排序
        macro = macro.sort_values('trade_date')
        idx = idx.sort_values('trade_date')

        # 宏观列 (排除 trade_date)
        macro_cols = [c for c in macro.columns if c != 'trade_date']

        # 使用 merge_asof: 找到 <= index trade_date 的最近宏观数据
        merged = pd.merge_asof(
            idx, macro[['trade_date'] + macro_cols],
            on='trade_date',
            direction='backward'
        )

        return merged
