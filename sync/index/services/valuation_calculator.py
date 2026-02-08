"""
估值指标计算服务

计算指数的加权 PE/PB 和等权 PE/PB
"""

from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd

from entity.stock_daily_basic import StockDailyBasic
from entity.stock_weight import StockWeight
from mysql_connect.stock_basic_mapper import StockBasicMapper
from mysql_connect.stock_daily_basic_mapper import StockDailyBasicMapper
from mysql_connect.stock_weight_mapper import StockWeightMapper
from util.class_util import ClassUtil
from util.date_util import TimeUtils


class ValuationCalculator:
    """
    估值指标计算服务
    
    职责：
    - 计算加权 PE/PB（基于指数权重）
    - 计算等权 PE/PB（基于市值权重）
    - 获取成分股权重数据
    """
    
    def __init__(self,
                 stock_weight_mapper: Optional[StockWeightMapper] = None,
                 stock_basic_mapper: Optional[StockBasicMapper] = None,
                 stock_daily_basic_mapper: Optional[StockDailyBasicMapper] = None):
        """
        初始化估值计算服务
        
        Args:
            stock_weight_mapper: 股票权重 Mapper
            stock_basic_mapper: 股票基础信息 Mapper
            stock_daily_basic_mapper: 股票日线基础数据 Mapper
        """
        self.stock_weight_mapper = stock_weight_mapper or StockWeightMapper()
        self.stock_basic_mapper = stock_basic_mapper or StockBasicMapper()
        self.stock_daily_basic_mapper = stock_daily_basic_mapper or StockDailyBasicMapper()
    
    def calculate_index_pe_pb(self, index_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        计算指数在指定时间段内的加权 PE/PB 和等权 PE/PB
        
        Args:
            index_code: 指数代码
            start_date: 开始日期 (YYYYMMDD 格式字符串)
            end_date: 结束日期 (YYYYMMDD 格式字符串)
        
        Returns:
            pd.DataFrame: 包含每日加权 PE/PB 和等权 PE/PB 的数据
        """
        # 将日期字符串转换为 datetime 对象
        start_dt = datetime.strptime(start_date, '%Y%m%d')
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        
        print(f"开始计算指数 {index_code} 从 {start_dt.strftime('%Y-%m-%d')} 到 {end_dt.strftime('%Y-%m-%d')} 的 PE/PB")
        
        # 1. 获取所有成分股代码
        con_code_list = self._get_all_con_codes(index_code, start_dt, end_dt)
        
        if not con_code_list:
            print("未找到成分股数据")
            return pd.DataFrame()
        
        # 2. 获取最新的成分股权重
        monthly_stock_info = self._get_monthly_stock_weights(index_code, con_code_list, start_dt, end_dt)
        
        if monthly_stock_info is None or monthly_stock_info.empty:
            print("未找到任何成分股权重数据")
            return pd.DataFrame()
        
        print(f"找到 {len(con_code_list)} 只成分股")
        
        # 3. 计算每日加权 PE/PB 和等权 PE/PB
        result_data = self._calculate_both_weighted_metrics(
            monthly_stock_info, con_code_list, start_dt, end_dt
        )
        
        print(f"计算完成，共生成 {len(result_data)} 条记录")
        return pd.DataFrame(result_data)
    
    def _get_all_con_codes(self, index_code: str, start_date: datetime, end_date: datetime) -> List[str]:
        """获取指定时间段内的所有成分股代码"""
        start_date_str = TimeUtils.date_to_str(start_date)
        end_date_str = TimeUtils.date_to_str(end_date)
        return self.stock_weight_mapper.get_exist_con_code(
            index_code=index_code, start_date=start_date_str, end_date=end_date_str
        )
    
    def _get_monthly_stock_weights(self, index_code: str, con_code_list: List[str],
                                   start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """获取最新的成分股权重数据"""
        start_date_str = TimeUtils.date_to_str(start_date)
        end_date_str = TimeUtils.date_to_str(end_date)
        
        if not con_code_list:
            return None
        
        data = self.stock_weight_mapper.get_newest_weight_by_con_code_list(
            index_code=index_code, con_code_list=con_code_list,
            start_date=start_date_str, end_date=end_date_str
        )
        
        if not data:
            return None
        
        weight_list = []
        for row in data:
            weight = ClassUtil.create_entities_from_data(StockWeight, row)
            weight_list.append(weight.to_dict())
        
        return pd.DataFrame(weight_list)
    
    def _calculate_both_weighted_metrics(self, monthly_stock_info: pd.DataFrame,
                                        consistent_stocks: List[str],
                                        start_date: datetime, end_date: datetime) -> List[dict]:
        """计算加权 PE/PB 和等权 PE/PB 指标"""
        result_data = []
        
        if monthly_stock_info is None or monthly_stock_info.empty:
            return result_data
        
        current_month_start = start_date
        while current_month_start <= end_date:
            # 计算当前月份的结束日期
            next_month_start = (current_month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            current_month_end = next_month_start - timedelta(days=1)
            
            # 确保不超过 end_date
            if current_month_end > end_date:
                current_month_end = end_date
            
            # 计算当前月份每天的加权指标
            current_date = current_month_start
            while current_date <= current_month_end:
                date_str = current_date.strftime('%Y%m%d')
                financial_data = self.stock_daily_basic_mapper.select_by_trade_date_and_ts_code(
                    date_str, consistent_stocks
                )
                
                financial_data_info = []
                for row in financial_data:
                    stock_data = ClassUtil.create_entities_from_data(StockDailyBasic, row)
                    financial_data_info.append(stock_data.to_dict())
                
                if financial_data:
                    daily_result = self._calculate_daily_both_metrics(
                        financial_data_info, monthly_stock_info, date_str
                    )
                    if daily_result:
                        result_data.append(daily_result)
                
                current_date += timedelta(days=1)
            
            current_month_start = next_month_start
        
        return result_data
    
    def _calculate_daily_both_metrics(self, daily_financial_data: List[dict],
                                     month_weights: pd.DataFrame, trade_date: str) -> Optional[dict]:
        """计算单日的加权指标和等权指标"""
        financial_df = pd.DataFrame(daily_financial_data)
        
        # 合并财务数据和权重
        merged_df = pd.merge(
            financial_df,
            month_weights[['con_code', 'weight']],
            left_on='ts_code',
            right_on='con_code',
            how='inner'
        )
        
        if merged_df.empty:
            return None
        
        # 计算加权指标（基于指数权重）
        weighted_metrics = self._calculate_index_weighted_metrics(merged_df)
        
        # 计算等权指标（基于市值权重）
        equal_weight_metrics = self._calculate_market_cap_weighted_metrics(merged_df)
        
        # 合并结果
        result = {
            'trade_date': trade_date,
            # 指数权重加权指标
            'weighted_pe': weighted_metrics['pe'],
            'weighted_pe_ttm': weighted_metrics['pe_ttm'],
            'weighted_pb': weighted_metrics['pb'],
            # 市值权重等权指标
            'equal_weight_pe': equal_weight_metrics['pe'],
            'equal_weight_pe_ttm': equal_weight_metrics['pe_ttm'],
            'equal_weight_pb': equal_weight_metrics['pb'],
            # 统计信息
            'valid_stocks_pe': weighted_metrics['valid_pe_count'],
            'valid_stocks_pe_ttm': weighted_metrics['valid_pe_ttm_count'],
            'valid_stocks_pb': weighted_metrics['valid_pb_count'],
            'total_stocks': len(merged_df),
            'weighted_pe_dedt': weighted_metrics['pe_dedt'],
            'weighted_pe_ttm_dedt': weighted_metrics['pe_ttm_dedt']
        }
        
        return result
    
    def _calculate_index_weighted_metrics(self, merged_df: pd.DataFrame) -> dict:
        """计算基于指数权重的加权指标"""
        # 初始化累计值
        weighted_total_net_profit = 0
        weighted_total_net_profit_ttm = 0
        weighted_total_net_profit_dedt = 0
        weighted_total_net_profit_ttm_dedt = 0
        weighted_total_net_assets = 0
        weighted_total_circ_mv_pe = 0
        weighted_total_circ_mv_pe_ttm = 0
        weighted_total_circ_mv_pb = 0
        weighted_total_circ_mv_pe_dedt = 0
        weighted_total_circ_mv_pe_ttm_dedt = 0
        
        valid_pe_count = 0
        valid_pe_ttm_count = 0
        valid_pb_count = 0
        
        for _, row in merged_df.iterrows():
            weight = row['weight'] / 100.0  # 假设权重是百分比
            total_mv = row['total_mv']
            circ_mv = row['circ_mv']
            
            # 计算 PE 相关指标
            if pd.notna(row['pe']) and row['pe'] > 0:
                net_profit = total_mv / row['pe']
                weighted_total_net_profit += net_profit * weight
                weighted_total_circ_mv_pe += circ_mv * weight
                valid_pe_count += 1
            else:
                weighted_total_circ_mv_pe += circ_mv * weight
                valid_pe_count += 1
            
            # 计算 PE_TTM 相关指标
            if pd.notna(row['pe_ttm']) and row['pe_ttm'] > 0:
                net_profit_ttm = total_mv / row['pe_ttm']
                weighted_total_net_profit_ttm += net_profit_ttm * weight
                weighted_total_circ_mv_pe_ttm += circ_mv * weight
                valid_pe_ttm_count += 1
            else:
                weighted_total_circ_mv_pe_ttm += circ_mv * weight
                valid_pe_ttm_count += 1
            
            # 计算 PB 相关指标
            if pd.notna(row['pb']) and row['pb'] > 0:
                net_assets = total_mv / row['pb']
                weighted_total_net_assets += net_assets * weight
                weighted_total_circ_mv_pb += circ_mv * weight
                valid_pb_count += 1
            else:
                weighted_total_circ_mv_pb += circ_mv * weight
                valid_pb_count += 1
            
            # 计算扣非 PE 相关指标
            if 'pe_profit_dedt' in row and pd.notna(row['pe_profit_dedt']) and row['pe_profit_dedt'] > 0:
                weighted_total_circ_mv_pe_dedt += circ_mv * weight
                weighted_total_net_profit_dedt += circ_mv / row['pe_profit_dedt'] * weight
            else:
                weighted_total_circ_mv_pe_dedt += circ_mv * weight
            
            # 计算扣非 PE_TTM 相关指标
            if 'pe_ttm_profit_dedt' in row and pd.notna(row['pe_ttm_profit_dedt']) and row['pe_ttm_profit_dedt'] > 0:
                weighted_total_circ_mv_pe_ttm_dedt += circ_mv * weight
                weighted_total_net_profit_ttm_dedt += circ_mv / row['pe_ttm_profit_dedt'] * weight
            else:
                weighted_total_circ_mv_pe_ttm_dedt += circ_mv * weight
        
        # 计算最终的加权指标
        weighted_pe = (weighted_total_circ_mv_pe / weighted_total_net_profit
                      if weighted_total_net_profit > 0 else None)
        weighted_pe_ttm = (weighted_total_circ_mv_pe_ttm / weighted_total_net_profit_ttm
                          if weighted_total_net_profit_ttm > 0 else None)
        weighted_pb = (weighted_total_circ_mv_pb / weighted_total_net_assets
                      if weighted_total_net_assets > 0 else None)
        weighted_pe_dedt = (weighted_total_circ_mv_pe_dedt / weighted_total_net_profit_dedt
                           if weighted_total_net_profit_dedt > 0 else None)
        weighted_pe_ttm_dedt = (weighted_total_circ_mv_pe_ttm_dedt / weighted_total_net_profit_ttm_dedt
                               if weighted_total_net_profit_ttm_dedt > 0 else None)
        
        return {
            'pe': weighted_pe,
            'pe_ttm': weighted_pe_ttm,
            'pb': weighted_pb,
            'pe_dedt': weighted_pe_dedt,
            'pe_ttm_dedt': weighted_pe_ttm_dedt,
            'valid_pe_count': valid_pe_count,
            'valid_pe_ttm_count': valid_pe_ttm_count,
            'valid_pb_count': valid_pb_count
        }
    
    def _calculate_market_cap_weighted_metrics(self, merged_df: pd.DataFrame) -> dict:
        """计算基于市值权重的等权指标"""
        # 过滤有效数据
        valid_data = merged_df.dropna(subset=['total_mv'])
        
        if valid_data.empty:
            return {'pe': None, 'pe_ttm': None, 'pb': None}
        
        # 计算总市值
        total_market_cap = valid_data['total_mv'].sum()
        
        if total_market_cap <= 0:
            return {'pe': None, 'pe_ttm': None, 'pb': None}
        
        # 计算总流通市值
        circ_market_cap = valid_data['circ_mv'].sum()
        
        # 初始化累计值
        mv_weighted_net_profit = 0
        mv_weighted_net_profit_ttm = 0
        mv_weighted_net_assets = 0
        mv_weighted_total_mv_pe = 0
        mv_weighted_total_mv_pe_ttm = 0
        mv_weighted_total_mv_pb = 0
        
        weighted_total_net_profit_dedt = 0
        weighted_total_net_profit_ttm_dedt = 0
        weighted_total_circ_mv_pe_dedt = 0
        weighted_total_circ_mv_pe_ttm_dedt = 0
        
        for _, row in valid_data.iterrows():
            total_mv = row['total_mv']
            mv_weight = total_mv / total_market_cap  # 市值权重
            circ_mv = row['circ_mv']
            circ_mv_weight = circ_mv / circ_market_cap if circ_market_cap > 0 else 0
            
            # 计算 PE 相关指标
            if pd.notna(row['pe']) and row['pe'] > 0:
                net_profit = total_mv / row['pe']
                mv_weighted_net_profit += net_profit * mv_weight
                mv_weighted_total_mv_pe += total_mv * mv_weight
            
            # 计算 PE_TTM 相关指标
            if pd.notna(row['pe_ttm']) and row['pe_ttm'] > 0:
                net_profit_ttm = total_mv / row['pe_ttm']
                mv_weighted_net_profit_ttm += net_profit_ttm * mv_weight
                mv_weighted_total_mv_pe_ttm += total_mv * mv_weight
            
            # 计算 PB 相关指标
            if pd.notna(row['pb']) and row['pb'] > 0:
                net_assets = total_mv / row['pb']
                mv_weighted_net_assets += net_assets * mv_weight
                mv_weighted_total_mv_pb += total_mv * mv_weight
            
            # 计算扣非 PE 相关指标
            if 'pe_profit_dedt' in row and pd.notna(row['pe_profit_dedt']) and row['pe_profit_dedt'] > 0:
                weighted_total_circ_mv_pe_dedt += circ_mv * circ_mv_weight
                weighted_total_net_profit_dedt += circ_mv / row['pe_profit_dedt'] * circ_mv_weight
            
            # 计算扣非 PE_TTM 相关指标
            if 'pe_ttm_profit_dedt' in row and pd.notna(row['pe_ttm_profit_dedt']) and row['pe_ttm_profit_dedt'] > 0:
                weighted_total_circ_mv_pe_ttm_dedt += circ_mv * circ_mv_weight
                weighted_total_net_profit_ttm_dedt += circ_mv / row['pe_ttm_profit_dedt'] * circ_mv_weight
        
        # 计算最终的市值加权指标
        equal_weight_pe = (mv_weighted_total_mv_pe / mv_weighted_net_profit
                          if mv_weighted_net_profit > 0 else None)
        equal_weight_pe_ttm = (mv_weighted_total_mv_pe_ttm / mv_weighted_net_profit_ttm
                              if mv_weighted_net_profit_ttm > 0 else None)
        equal_weight_pb = (mv_weighted_total_mv_pb / mv_weighted_net_assets
                          if mv_weighted_net_assets > 0 else None)
        weighted_pe_dedt = (weighted_total_circ_mv_pe_dedt / weighted_total_net_profit_dedt
                           if weighted_total_net_profit_dedt > 0 else None)
        weighted_pe_ttm_dedt = (weighted_total_circ_mv_pe_ttm_dedt / weighted_total_net_profit_ttm_dedt
                               if weighted_total_net_profit_ttm_dedt > 0 else None)
        
        return {
            'pe': equal_weight_pe,
            'pe_ttm': equal_weight_pe_ttm,
            'pb': equal_weight_pb,
            'weighted_pe_dedt': weighted_pe_dedt,
            'weighted_pe_ttm_dedt': weighted_pe_ttm_dedt
        }
