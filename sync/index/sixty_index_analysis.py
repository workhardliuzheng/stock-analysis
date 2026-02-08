"""
指数数据同步与分析模块

重构后的主协调器，职责：
- 协调各个服务模块的调用
- 实现增量同步逻辑
- 管理数据流程
"""

from typing import List, Optional

import pandas as pd

from analysis.deviation_rate_calculator import DeviationRateCalculator
from analysis.technical_indicator_calculator import TechnicalIndicatorCalculator
from analysis.cross_signal_detector import CrossSignalDetector
from analysis.percentile_calculator import PercentileCalculator
from entity import constant
from entity.stock_data import StockData
from mysql_connect.sixty_index_mapper import SixtyIndexMapper
from sync.index.services.index_data_fetcher import IndexDataFetcher
from sync.index.services.valuation_calculator import ValuationCalculator
from util.date_util import TimeUtils

# 全局 Mapper 实例
mapper = SixtyIndexMapper()


class SixtyIndexAnalysis:
    """
    指数数据同步与分析类
    
    主要功能：
    - 增量同步指数行情数据
    - 计算技术指标（MA、MACD、RSI、KDJ、布林带等）
    - 计算估值指标（PE、PB）
    - 计算偏离率（JSON 格式存储）
    - 计算交叉信号（均线金叉死叉、MACD金叉死叉）
    - 计算历史百分位（各指标的5年百分位）
    """
    
    # 技术指标计算配置
    MA_PERIODS = [5, 10, 20, 50]
    WMA_PERIODS = [5, 10, 20, 50]
    BATCH_SIZE = 100
    PERCENTILE_LOOKBACK_YEARS = 5
    
    def __init__(self):
        """初始化服务组件"""
        self.data_fetcher = IndexDataFetcher()
        self.tech_calculator = TechnicalIndicatorCalculator(
            ma_periods=self.MA_PERIODS,
            wma_periods=self.WMA_PERIODS
        )
        self.deviation_calculator = DeviationRateCalculator(
            ma_periods=self.MA_PERIODS
        )
        self.cross_detector = CrossSignalDetector()
        self.percentile_calculator = PercentileCalculator(
            lookback_years=self.PERCENTILE_LOOKBACK_YEARS
        )
        self.valuation_calculator = ValuationCalculator()
    
    def additional_data(self, pe_cal_start_date: str):
        """
        增量同步所有指数数据
        
        新流程：
        1. 查询增量起始日期
        2. 批量获取行情数据
        3. 计算技术指标
        4. 计算偏离率 JSON
        5. 计算交叉信号（均线金叉死叉、MACD金叉死叉）
        6. 计算历史百分位（5年窗口）
        7. 过滤增量数据
        8. 批量插入数据库
        9. 更新 PE/PB 数据
        
        Args:
            pe_cal_start_date: PE/PB 计算的起始日期
        """
        for ts_code in constant.TS_CODE_LIST:
            try:
                self._sync_single_index(ts_code, pe_cal_start_date)
            except Exception as e:
                print(f"同步指数 {ts_code} 失败: {e}")
                continue
    
    def _sync_single_index(self, ts_code: str, pe_cal_start_date: str):
        """
        同步单个指数的数据
        
        Args:
            ts_code: 指数代码
            pe_cal_start_date: PE/PB 计算起始日期
        """
        index_name = constant.TS_CODE_NAME_DICT.get(ts_code, ts_code)
        print(f"\n开始同步指数 {index_name} ({ts_code})")
        
        # 1. 查询增量起始日期
        max_trade_date = mapper.get_max_trade_time(ts_code)
        if max_trade_date is None:
            start_date = constant.HISTORY_START_DATE_MAP.get(ts_code, '20150101')
        else:
            start_date = TimeUtils.get_n_days_before_or_after(
                TimeUtils.date_to_str(max_trade_date), 1, is_before=False
            )
        end_date = TimeUtils.get_current_date_str()
        
        print(f"  同步日期范围: {start_date} - {end_date}")
        
        # 2. 批量获取行情数据
        market_df = self.data_fetcher.fetch_index_daily(ts_code, start_date, end_date)
        
        if market_df.empty:
            print(f"  指数 {index_name} 无新数据需要同步")
            return
        
        print(f"  获取到 {len(market_df)} 条行情数据")
        
        # 3. 计算技术指标
        market_df = self.tech_calculator.calculate(market_df)
        
        # 4. 计算偏离率 JSON
        market_df = self.deviation_calculator.calculate(market_df)
        
        # 5. 计算交叉信号（均线金叉死叉、MACD金叉死叉）
        market_df = self.cross_detector.detect(market_df)
        print(f"  交叉信号计算完成")
        
        # 6. 计算历史百分位（需要全量历史数据）
        market_df = self.percentile_calculator.calculate(market_df)
        print(f"  历史百分位计算完成")
        
        # 7. 过滤只保留需要同步的日期范围内的数据
        market_df = market_df[market_df['trade_date'] >= start_date].reset_index(drop=True)
        
        if market_df.empty:
            print(f"  过滤后无新数据需要同步")
            return
        
        print(f"  过滤后 {len(market_df)} 条数据需要同步")
        
        # 8. 转换为 StockData 对象并批量插入
        stock_data_list = self._convert_to_stock_data(market_df, ts_code)
        self._batch_upsert(stock_data_list)
        
        print(f"  行情数据同步完成")
        
        # 9. 更新 PE/PB 数据
        self._update_pe_pb_data(ts_code, pe_cal_start_date, end_date)
    
    def _convert_to_stock_data(self, df: pd.DataFrame, ts_code: str) -> List[StockData]:
        """
        将 DataFrame 转换为 StockData 对象列表
        
        Args:
            df: 包含行情和技术指标的 DataFrame
            ts_code: 指数代码
        
        Returns:
            List[StockData]: StockData 对象列表
        """
        stock_data_list = []
        index_name = constant.TS_CODE_NAME_DICT.get(ts_code, ts_code)
        
        for _, row in df.iterrows():
            stock_data = StockData(
                ts_code=ts_code,
                trade_date=str(row['trade_date']),
                close=self._safe_float(row.get('close')),
                open=self._safe_float(row.get('open')),
                high=self._safe_float(row.get('high')),
                low=self._safe_float(row.get('low')),
                pre_close=self._safe_float(row.get('pre_close')),
                change=self._safe_float(row.get('change')),
                pct_chg=self._safe_float(row.get('pct_chg')),
                vol=self._safe_float(row.get('vol')),
                amount=self._safe_float(row.get('amount')) / 10 if row.get('amount') else None,
                name=index_name,
                deviation_rate=row.get('deviation_rate'),
                # 技术指标
                ma_5=self._safe_float(row.get('ma_5')),
                ma_10=self._safe_float(row.get('ma_10')),
                ma_20=self._safe_float(row.get('ma_20')),
                ma_50=self._safe_float(row.get('ma_50')),
                wma_5=self._safe_float(row.get('wma_5')),
                wma_10=self._safe_float(row.get('wma_10')),
                wma_20=self._safe_float(row.get('wma_20')),
                wma_50=self._safe_float(row.get('wma_50')),
                macd=self._safe_float(row.get('macd')),
                macd_signal_line=self._safe_float(row.get('macd_signal_line')),
                macd_histogram=self._safe_float(row.get('macd_histogram')),
                rsi=self._safe_float(row.get('rsi')),
                kdj_k=self._safe_float(row.get('kdj_k')),
                kdj_d=self._safe_float(row.get('kdj_d')),
                kdj_j=self._safe_float(row.get('kdj_j')),
                bb_high=self._safe_float(row.get('bb_high')),
                bb_mid=self._safe_float(row.get('bb_mid')),
                bb_low=self._safe_float(row.get('bb_low')),
                obv=self._safe_float(row.get('obv')),
                cross_signals=row.get('cross_signals'),
                percentile_ranks=row.get('percentile_ranks')
            )
            stock_data_list.append(stock_data)
        
        return stock_data_list
    
    def _batch_upsert(self, stock_data_list: List[StockData]):
        """
        批量插入或更新数据
        
        Args:
            stock_data_list: StockData 对象列表
        """
        total = len(stock_data_list)
        for i in range(0, total, self.BATCH_SIZE):
            batch = stock_data_list[i:i + self.BATCH_SIZE]
            try:
                mapper.upsert_batch(batch)
                print(f"    已处理 {min(i + self.BATCH_SIZE, total)}/{total} 条数据")
            except Exception as e:
                print(f"    批量插入失败: {e}")
                # 尝试单条插入
                for data in batch:
                    try:
                        mapper.insert_index(data)
                    except Exception as single_error:
                        print(f"    单条插入失败: {single_error}")
    
    def _update_pe_pb_data(self, ts_code: str, start_date: str, end_date: str):
        """
        更新 PE/PB 数据
        
        Args:
            ts_code: 指数代码
            start_date: 开始日期
            end_date: 结束日期
        """
        try:
            print(f"  开始计算 PE/PB 数据...")
            pe_pb_df = self.valuation_calculator.calculate_index_pe_pb(ts_code, start_date, end_date)
            
            if pe_pb_df.empty:
                print(f"  无 PE/PB 数据")
                return
            
            # 转换为 StockData 并批量更新
            update_fields = [
                'pb_weight', 'pe_weight', 'pe_ttm_weight',
                'pb', 'pe', 'pe_ttm',
                'pe_profit_dedt', 'pe_profit_dedt_ttm'
            ]
            
            for _, row in pe_pb_df.iterrows():
                stock_data = StockData(
                    ts_code=ts_code,
                    trade_date=str(row['trade_date']),
                    pb_weight=self._safe_float(row.get('weighted_pb')),
                    pe_weight=self._safe_float(row.get('weighted_pe')),
                    pe_ttm_weight=self._safe_float(row.get('weighted_pe_ttm')),
                    pb=self._safe_float(row.get('equal_weight_pb')),
                    pe=self._safe_float(row.get('equal_weight_pe')),
                    pe_ttm=self._safe_float(row.get('equal_weight_pe_ttm')),
                    pe_profit_dedt=self._safe_float(row.get('weighted_pe_dedt')),
                    pe_profit_dedt_ttm=self._safe_float(row.get('weighted_pe_ttm_dedt'))
                )
                mapper.update_by_ts_code_and_trade_date(stock_data, update_fields)
            
            print(f"  PE/PB 数据更新完成，共 {len(pe_pb_df)} 条")
            
        except Exception as e:
            print(f"  更新 PE/PB 数据失败: {e}")
    
    @staticmethod
    def _safe_float(value) -> Optional[float]:
        """安全转换为 float，处理 NaN 和 None"""
        if value is None:
            return None
        if pd.isna(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    # =========== 技术指标单独更新方法（保留兼容性）===========
    
    def additional_tech_data_and_update_mapper(self, index_code: str, start_date: str,
                                               end_date: str, batch_size: int = 100):
        """
        获取指数技术指标数据并批量更新到数据库
        
        Args:
            index_code: 指数代码
            start_date: 开始日期
            end_date: 结束日期
            batch_size: 批量大小
        """
        try:
            index_name = constant.TS_CODE_NAME_DICT.get(index_code, index_code)
            print(f"开始获取指数 {index_name} 的技术指标...")
            
            # 从数据库获取数据
            data = mapper.select_by_code_and_trade_round(index_code, start_date, end_date)
            if not data:
                print(f"指数 {index_name} 在 {start_date}-{end_date} 期间无数据")
                return
            
            # 转换为 DataFrame
            from util.class_util import ClassUtil
            data_frame_list = []
            for row in data:
                stock_data = ClassUtil.create_entities_from_data(StockData, row)
                data_frame_list.append(stock_data.to_dict())
            
            df = pd.DataFrame(data_frame_list)
            
            # 计算技术指标
            df = self.tech_calculator.calculate(df)
            
            # 计算偏离率
            df = self.deviation_calculator.calculate(df)
            
            # 计算交叉信号
            df = self.cross_detector.detect(df)
            
            # 计算历史百分位
            df = self.percentile_calculator.calculate(df)
            
            print(f"获取到 {len(df)} 条技术指标数据，开始批量更新...")
            
            # 更新字段
            update_fields = [
                'ma_5', 'ma_10', 'ma_20', 'ma_50',
                'wma_5', 'wma_10', 'wma_20', 'wma_50',
                'macd', 'macd_signal_line', 'macd_histogram',
                'rsi', 'kdj_k', 'kdj_d', 'kdj_j',
                'bb_high', 'bb_mid', 'bb_low', 'obv',
                'deviation_rate', 'cross_signals', 'percentile_ranks'
            ]
            
            total_updated = 0
            for _, row in df.iterrows():
                stock_data = StockData(
                    ts_code=index_code,
                    trade_date=str(row['trade_date']),
                    ma_5=self._safe_float(row.get('ma_5')),
                    ma_10=self._safe_float(row.get('ma_10')),
                    ma_20=self._safe_float(row.get('ma_20')),
                    ma_50=self._safe_float(row.get('ma_50')),
                    wma_5=self._safe_float(row.get('wma_5')),
                    wma_10=self._safe_float(row.get('wma_10')),
                    wma_20=self._safe_float(row.get('wma_20')),
                    wma_50=self._safe_float(row.get('wma_50')),
                    macd=self._safe_float(row.get('macd')),
                    macd_signal_line=self._safe_float(row.get('macd_signal_line')),
                    macd_histogram=self._safe_float(row.get('macd_histogram')),
                    rsi=self._safe_float(row.get('rsi')),
                    kdj_k=self._safe_float(row.get('kdj_k')),
                    kdj_d=self._safe_float(row.get('kdj_d')),
                    kdj_j=self._safe_float(row.get('kdj_j')),
                    bb_high=self._safe_float(row.get('bb_high')),
                    bb_mid=self._safe_float(row.get('bb_mid')),
                    bb_low=self._safe_float(row.get('bb_low')),
                    obv=self._safe_float(row.get('obv')),
                    deviation_rate=row.get('deviation_rate'),
                    cross_signals=row.get('cross_signals'),
                    percentile_ranks=row.get('percentile_ranks')
                )
                mapper.update_by_ts_code_and_trade_date(stock_data, update_fields)
                total_updated += 1
            
            print(f"技术指标数据更新完成，共成功更新 {total_updated} 条数据")
            
        except Exception as e:
            print(f"更新技术指标数据时发生错误: {e}")
            raise e
    
    def additional_pe_data_and_update_mapper(self, index_code: str, start_date: str,
                                            end_date: str, batch_size: int = 100):
        """
        获取指数 PE/PB 数据并批量更新到数据库
        
        Args:
            index_code: 指数代码
            start_date: 开始日期
            end_date: 结束日期
            batch_size: 批量大小
        """
        self._update_pe_pb_data(index_code, start_date, end_date)
