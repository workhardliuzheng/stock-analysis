from datetime import datetime, timedelta
import time

import pandas as pd
import tushare as ts
import yaml

from entity import constant
from entity.stock_data import StockData
from entity.stock_weight import StockWeight
from mysql_connect.common_mapper import CommonMapper
from mysql_connect.sixty_index_mapper import SixtyIndexMapper
from mysql_connect.stock_weight_mapper import StockWeightMapper
from sync.index.sync_stock_weight import additional_data
from tu_share_factory.tu_share_factory import TuShareFactory
from util.class_util import ClassUtil
from util.date_util import TimeUtils

INDEX_FIELDS=["ts_code","trade_date","open","high","low","close","pre_close","change","pct_chg","vol","amount"]
TRADE_CAL_FIELDS= [
    "exchange",
    "cal_date",
    "is_open",
    "pretrade_date"
]

mapper = SixtyIndexMapper()
stock_weight_mapper = StockWeightMapper()

class SixtyIndexAnalysis:

    # 同步今日往前的所有书籍
    def sync_history_value(self):
        for ts_code in constant.TS_CODE_LIST:
            history_start_date = constant.HISTORY_START_DATE_MAP[ts_code]
            self.init_sixty_index_average_value(ts_code, history_start_date, TimeUtils.get_current_date_str())

    # 同步今日往的书籍
    def sync_today_value(self):
        for ts_code in constant.TS_CODE_LIST:
            self.init_sixty_index_average_value(ts_code, TimeUtils.get_current_date_str(), TimeUtils.get_current_date_str())

    # 自动同步数据
    def additional_data(self):
        # 同步权重
        additional_data()
        # 同步指数价值
        for ts_code in constant.TS_CODE_LIST:
            history_start_date = constant.HISTORY_START_DATE_MAP[ts_code]
            mapper = SixtyIndexMapper()
            max_trade_datetime = mapper.get_max_trade_time(ts_code)
            if max_trade_datetime is None:
                max_trade_date = history_start_date
            else:
                max_trade_date = TimeUtils.date_to_str(max_trade_datetime)
            start_date = TimeUtils.get_n_days_before_or_after(max_trade_date, 1, True)
            self.init_sixty_index_average_value(ts_code, start_date, TimeUtils.get_current_date_str())
            self.additional_pe_data_and_update_mapper(ts_code, constant.HISTORY_START_DATE_MAP[ts_code], TimeUtils.get_current_date_str())




    def init_sixty_index_average_value(self, ts_code, start_date, end_date):
        pro = TuShareFactory.build_api_client()

        this_loop_date = start_date
        # endDate不包含当天
        while TimeUtils.compare_date_str(this_loop_date, end_date) <= 0 :
            this_loop_end_date = TimeUtils.get_n_days_before_or_after(this_loop_date, 100, is_before=False)
            # 停牌日不计算
            exchange = "SZSE" if ts_code.endswith("SZ") else "SSE"
            trade_cal = pro.trade_cal(**{
                "exchange": exchange,
                "start_date": this_loop_date,
                "end_date": this_loop_end_date
            }, fields=TRADE_CAL_FIELDS)
            trade_cal = trade_cal.sort_index(ascending=False)

            # 获取一段时间的数据
            date_ago = TimeUtils.get_n_days_before_or_after(this_loop_date, 100, is_before=True)
            daily = pro.index_daily(**{
                "ts_code": ts_code,
                "start_date": date_ago,
                "end_date": this_loop_end_date,
                "limit": 250
            }, fields=INDEX_FIELDS)

            if len(daily) < 60:
                this_loop_date = TimeUtils.get_n_days_before_or_after(this_loop_date, 60-len(daily), False)
                continue

            for row in trade_cal.itertuples():
                if row.is_open == 0:
                    continue
                # 取出最近60天的数据
                sixty_date = daily[daily['trade_date'] <= row.cal_date].head(60)

                sixty_index_average_value = sixty_date['close'].mean()
                now_days_value = sixty_date.iloc[0]
                deviation_rate = now_days_value['close'] / sixty_index_average_value - 1
                # 生成数据
                stock_data = StockData(id=None,
                                       ts_code=now_days_value['ts_code'],
                                       trade_date=now_days_value['trade_date'],
                                       close=float(now_days_value['close']),
                                       open=float(now_days_value['open']),
                                       high=float(now_days_value['high']),
                                       low=float(now_days_value['low']),
                                       pre_close=float(now_days_value['pre_close']),
                                       change=float(now_days_value['change']),
                                       pct_chg=float(now_days_value['pct_chg']),
                                       vol=float(now_days_value['vol']),
                                       amount=float(now_days_value['amount'] / 10),
                                       average_date=60,
                                       average_amount=float(sixty_index_average_value),
                                       deviation_rate=float(deviation_rate * 100),
                                       name=constant.TS_CODE_NAME_DICT[ts_code],
                                       pb_weight=0,
                                       pe_weight=0,
                                       pe_ttm_weight=0,
                                       pe_ttm=0,
                                       pb=0,
                                       pe=0)
                mapper.insert_index(stock_data)
                this_loop_date = row.cal_date

    def get_index_pe_pb(self, index_code, start_date, end_date):
        """
        计算指数在指定时间段内的加权PE/PB和等权PE/PB

        Args:
            index_code: 指数代码
            start_date: 开始日期 (YYYYMMDD格式字符串)
            end_date: 结束日期 (YYYYMMDD格式字符串)

        Returns:
            pd.DataFrame: 包含每日加权PE/PB和等权PE/PB的数据
        """
        pro = TuShareFactory.build_api_client()

        # 将日期字符串转换为datetime对象
        start_date = datetime.strptime(start_date, '%Y%m%d')
        end_date = datetime.strptime(end_date, '%Y%m%d')

        print(
            f"开始计算指数 {index_code} 从 {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')} 的PE/PB")

        # 1. 获取所有月份的成分股权重数据
        monthly_stock_info = self._get_monthly_stock_weights(index_code, start_date, end_date)

        if not monthly_stock_info:
            print("未找到任何成分股权重数据")
            return pd.DataFrame(columns=[
                'trade_date', 'weighted_pe', 'weighted_pe_ttm', 'weighted_pb',
                'equal_weight_pe', 'equal_weight_pe_ttm', 'equal_weight_pb'
            ])

        # 2. 分析股票在整个期间的存在情况
        stock_analysis = self._analyze_stock_existence(monthly_stock_info, start_date, end_date)

        if not stock_analysis['consistent_stocks']:
            print("未找到在整个期间都存在的股票")
            return pd.DataFrame(columns=[
                'trade_date', 'weighted_pe', 'weighted_pe_ttm', 'weighted_pb',
                'equal_weight_pe', 'equal_weight_pe_ttm', 'equal_weight_pb'
            ])

        print(f"找到 {len(stock_analysis['consistent_stocks'])} 只在整个期间都存在的股票")

        # 3. 获取财务数据
        financial_data = self._get_financial_data(pro, stock_analysis['consistent_stocks'], start_date, end_date)

        if not financial_data:
            print("未获取到财务数据")
            return pd.DataFrame(columns=[
                'trade_date', 'weighted_pe', 'weighted_pe_ttm', 'weighted_pb',
                'equal_weight_pe', 'equal_weight_pe_ttm', 'equal_weight_pb'
            ])

        # 4. 计算每日加权PE/PB和等权PE/PB
        result_data = self._calculate_both_weighted_metrics(monthly_stock_info, financial_data,
                                                            stock_analysis['consistent_stocks'],
                                                            start_date, end_date)

        print(f"计算完成，共生成 {len(result_data)} 条记录")
        return pd.DataFrame(result_data)

    def _get_monthly_stock_weights(self, index_code, start_date, end_date):
        """获取每个月的成分股权重数据"""
        monthly_stock_info = {}

        current_month_start = start_date
        while current_month_start <= end_date:
            # 计算当前月份的结束日期
            next_month_start = (current_month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            current_month_end = next_month_start - timedelta(days=1)

            try:
                # 获取当前月份的指数成分股及其权重
                stock = stock_weight_mapper.select_by_code_and_trade_round(
                    index_code=index_code,
                    start_date=current_month_start.strftime('%Y%m%d'),
                    end_date=current_month_end.strftime('%Y%m%d')
                )

                if stock:
                    stock_info = []
                    for row in stock:
                        stock_data = ClassUtil.create_entities_from_data(StockWeight, row)
                        stock_info.append(stock_data.to_dict())

                    if stock_info:
                        stock_df = pd.DataFrame(stock_info)
                        # 去重并存储，保留权重最大的记录
                        month_stock_info = stock_df.loc[stock_df.groupby('con_code')['weight'].idxmax()]
                        monthly_stock_info[current_month_start] = month_stock_info
                        print(f"月份 {current_month_start.strftime('%Y-%m')}: 获取到 {len(month_stock_info)} 只成分股")

            except Exception as e:
                print(f"获取月份 {current_month_start.strftime('%Y-%m')} 数据失败: {e}")

            # 移动到下一个月
            current_month_start = next_month_start

        return monthly_stock_info

    def _analyze_stock_existence(self, monthly_stock_info, start_date, end_date):
        """分析股票在整个期间的存在情况"""
        if not monthly_stock_info:
            return {'consistent_stocks': set(), 'all_stocks': set()}

        # 获取所有股票
        all_stocks = set()
        stock_monthly_presence = {}

        for month_start, stock_df in monthly_stock_info.items():
            month_stocks = set(stock_df['con_code'].tolist())
            all_stocks.update(month_stocks)

            for stock in month_stocks:
                if stock not in stock_monthly_presence:
                    stock_monthly_presence[stock] = []
                stock_monthly_presence[stock].append(month_start)

        # 计算总月份数
        total_months = len(monthly_stock_info)

        # 找到在所有月份都存在的股票
        consistent_stocks = set()
        for stock, months in stock_monthly_presence.items():
            if len(months) == total_months:
                # 进一步检查权重是否合理（大于0）
                is_valid = True
                for month_start in months:
                    stock_weight = monthly_stock_info[month_start]
                    stock_row = stock_weight[stock_weight['con_code'] == stock]
                    if stock_row.empty or stock_row.iloc[0]['weight'] <= 0:
                        is_valid = False
                        break

                if is_valid:
                    consistent_stocks.add(stock)

        print(f"股票存在性分析:")
        print(f"  总股票数: {len(all_stocks)}")
        print(f"  总月份数: {total_months}")
        print(f"  在所有月份都存在且权重>0的股票数: {len(consistent_stocks)}")

        return {
            'consistent_stocks': consistent_stocks,
            'all_stocks': all_stocks,
            'stock_monthly_presence': stock_monthly_presence
        }

    def _get_financial_data(self, pro, stock_codes, start_date, end_date):
        """获取财务数据"""
        financial_data = {}

        print(f"开始获取 {len(stock_codes)} 只股票的财务数据...")

        date_range = pd.date_range(start=start_date, end=end_date)
        total_days = len(date_range)

        for i, date in enumerate(date_range):
            date_str = date.strftime('%Y%m%d')

            try:
                time.sleep(0.3)  # 控制API调用频率
                df = pro.daily_basic(
                    trade_date=date_str,
                    fields='trade_date,ts_code,pe,pe_ttm,pb,total_mv,circ_mv'
                )

                if not df.empty:
                    # 只保留我们关心的股票
                    df_filtered = df[df['ts_code'].isin(stock_codes)]

                    if not df_filtered.empty:
                        # 只保留有效数据（total_mv和circ_mv不为空）
                        df_valid = df_filtered.dropna(subset=['total_mv', 'circ_mv'])

                        if not df_valid.empty:
                            financial_data[date_str] = df_valid.to_dict('records')

                if (i + 1) % 10 == 0:
                    print(f"  已获取 {i + 1}/{total_days} 天的数据")

            except Exception as e:
                print(f"获取 {date_str} 财务数据失败: {e}")
                continue

        print(f"财务数据获取完成，共 {len(financial_data)} 天有数据")
        return financial_data

    def _calculate_both_weighted_metrics(self, monthly_stock_info, financial_data, consistent_stocks, start_date,
                                         end_date):
        """计算加权PE/PB和等权PE/PB指标"""
        result_data = []

        current_month_start = start_date
        while current_month_start <= end_date:
            # 计算当前月份的结束日期
            next_month_start = (current_month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            current_month_end = next_month_start - timedelta(days=1)

            # 确保不超过end_date
            if current_month_end > end_date:
                current_month_end = end_date

            # 获取当前月份的权重数据
            if current_month_start not in monthly_stock_info:
                current_month_start = next_month_start
                continue

            month_weights = monthly_stock_info[current_month_start]
            # 只保留一致存在的股票
            month_weights = month_weights[month_weights['con_code'].isin(consistent_stocks)]

            if month_weights.empty:
                current_month_start = next_month_start
                continue

            # 计算当前月份每天的加权指标
            current_date = current_month_start
            while current_date <= current_month_end:
                date_str = current_date.strftime('%Y%m%d')

                if date_str in financial_data:
                    daily_result = self._calculate_daily_both_metrics(
                        financial_data[date_str], month_weights, date_str
                    )
                    if daily_result:
                        result_data.append(daily_result)

                current_date += timedelta(days=1)

            current_month_start = next_month_start

        return result_data

    def _calculate_daily_both_metrics(self, daily_financial_data, month_weights, trade_date):
        """计算单日的加权指标和等权指标"""
        # 转换为DataFrame便于处理
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
            'total_stocks': len(merged_df)
        }

        return result

    def _calculate_index_weighted_metrics(self, merged_df):
        """计算基于指数权重的加权指标"""
        # 初始化累计值
        weighted_total_net_profit = 0
        weighted_total_net_profit_ttm = 0
        weighted_total_net_assets = 0
        weighted_total_circ_mv_pe = 0
        weighted_total_circ_mv_pe_ttm = 0
        weighted_total_circ_mv_pb = 0

        valid_pe_count = 0
        valid_pe_ttm_count = 0
        valid_pb_count = 0

        for _, row in merged_df.iterrows():
            weight = row['weight'] / 100.0  # 假设权重是百分比
            total_mv = row['total_mv']
            circ_mv = row['circ_mv']

            # 计算PE相关指标
            if pd.notna(row['pe']) and row['pe'] > 0:
                net_profit = total_mv / row['pe']
                weighted_total_net_profit += net_profit * weight
                weighted_total_circ_mv_pe += circ_mv * weight
                valid_pe_count += 1

            # 计算PE_TTM相关指标
            if pd.notna(row['pe_ttm']) and row['pe_ttm'] > 0:
                net_profit_ttm = total_mv / row['pe_ttm']
                weighted_total_net_profit_ttm += net_profit_ttm * weight
                weighted_total_circ_mv_pe_ttm += circ_mv * weight
                valid_pe_ttm_count += 1

            # 计算PB相关指标
            if pd.notna(row['pb']) and row['pb'] > 0:
                net_assets = total_mv / row['pb']
                weighted_total_net_assets += net_assets * weight
                weighted_total_circ_mv_pb += circ_mv * weight
                valid_pb_count += 1

        # 计算最终的加权指标
        weighted_pe = (weighted_total_circ_mv_pe / weighted_total_net_profit
                       if weighted_total_net_profit > 0 else None)
        weighted_pe_ttm = (weighted_total_circ_mv_pe_ttm / weighted_total_net_profit_ttm
                           if weighted_total_net_profit_ttm > 0 else None)
        weighted_pb = (weighted_total_circ_mv_pb / weighted_total_net_assets
                       if weighted_total_net_assets > 0 else None)

        return {
            'pe': weighted_pe,
            'pe_ttm': weighted_pe_ttm,
            'pb': weighted_pb,
            'valid_pe_count': valid_pe_count,
            'valid_pe_ttm_count': valid_pe_ttm_count,
            'valid_pb_count': valid_pb_count
        }

    def _calculate_market_cap_weighted_metrics(self, merged_df):
        """计算基于市值权重的等权指标"""
        # 过滤有效数据
        valid_data = merged_df.dropna(subset=['total_mv'])

        if valid_data.empty:
            return {'pe': None, 'pe_ttm': None, 'pb': None}

        # 计算总市值
        total_market_cap = valid_data['total_mv'].sum()

        if total_market_cap <= 0:
            return {'pe': None, 'pe_ttm': None, 'pb': None}

        # 初始化累计值
        mv_weighted_net_profit = 0
        mv_weighted_net_profit_ttm = 0
        mv_weighted_net_assets = 0
        mv_weighted_total_mv_pe = 0
        mv_weighted_total_mv_pe_ttm = 0
        mv_weighted_total_mv_pb = 0

        for _, row in valid_data.iterrows():
            total_mv = row['total_mv']
            mv_weight = total_mv / total_market_cap  # 市值权重

            # 计算PE相关指标
            if pd.notna(row['pe']) and row['pe'] > 0:
                net_profit = total_mv / row['pe']
                mv_weighted_net_profit += net_profit * mv_weight
                mv_weighted_total_mv_pe += total_mv * mv_weight

            # 计算PE_TTM相关指标
            if pd.notna(row['pe_ttm']) and row['pe_ttm'] > 0:
                net_profit_ttm = total_mv / row['pe_ttm']
                mv_weighted_net_profit_ttm += net_profit_ttm * mv_weight
                mv_weighted_total_mv_pe_ttm += total_mv * mv_weight

            # 计算PB相关指标
            if pd.notna(row['pb']) and row['pb'] > 0:
                net_assets = total_mv / row['pb']
                mv_weighted_net_assets += net_assets * mv_weight
                mv_weighted_total_mv_pb += total_mv * mv_weight

        # 计算最终的市值加权指标
        equal_weight_pe = (mv_weighted_total_mv_pe / mv_weighted_net_profit
                           if mv_weighted_net_profit > 0 else None)
        equal_weight_pe_ttm = (mv_weighted_total_mv_pe_ttm / mv_weighted_net_profit_ttm
                               if mv_weighted_net_profit_ttm > 0 else None)
        equal_weight_pb = (mv_weighted_total_mv_pb / mv_weighted_net_assets
                           if mv_weighted_net_assets > 0 else None)

        return {
            'pe': equal_weight_pe,
            'pe_ttm': equal_weight_pe_ttm,
            'pb': equal_weight_pb
        }

    # 同时更新 additional_pe_data_and_update_mapper 方法
    def additional_pe_data_and_update_mapper(self, index_code, start_date, end_date, batch_size=100):
        """
        获取指数PE/PB数据并批量更新到数据库（包含等权指标）
        """
        try:
            print(f"开始获取指数 {index_code} 的PE/PB数据...")
            value = self.get_index_pe_pb(index_code=index_code, start_date=start_date, end_date=end_date)

            if value.empty:
                print(f"指数 {index_code} 在 {start_date}-{end_date} 期间无PE/PB数据")
                return

            print(f"获取到 {len(value)} 条PE/PB数据，开始批量更新...")

            # 数据验证和清理
            value = value.dropna(subset=['trade_date'])

            # 转换为StockData对象列表
            stock_data_list = []
            for index, row in value.iterrows():
                try:
                    stock_data = StockData(
                        id=None,
                        ts_code=index_code,
                        trade_date=str(row['trade_date']),
                        close=None, open=None, high=None, low=None,
                        pre_close=None, change=None, pct_chg=None,
                        vol=None, amount=None, average_date=None,
                        average_amount=None, deviation_rate=None, name=None,
                        # 指数权重加权指标
                        pb_weight=float(row['weighted_pb']) if pd.notna(row['weighted_pb']) else None,
                        pe_weight=float(row['weighted_pe']) if pd.notna(row['weighted_pe']) else None,
                        pe_ttm_weight=float(row['weighted_pe_ttm']) if pd.notna(row['weighted_pe_ttm']) else None,
                        # 市值权重等权指标
                        pb=float(row['equal_weight_pb']) if pd.notna(row['equal_weight_pb']) else None,
                        pe=float(row['equal_weight_pe']) if pd.notna(row['equal_weight_pe']) else None,
                        pe_ttm=float(row['equal_weight_pe_ttm']) if pd.notna(row['equal_weight_pe_ttm']) else None
                    )
                    stock_data_list.append(stock_data)
                except Exception as e:
                    print(f"创建StockData对象失败，跳过第 {index} 行: {e}")
                    continue

            if not stock_data_list:
                print("没有有效的数据需要更新")
                return

            # 分批更新
            total_updated = 0
            update_fields = ['pb_weight', 'pe_weight', 'pe_ttm_weight', 'pb', 'pe', 'pe_ttm']

            for i in range(0, len(stock_data_list), batch_size):
                batch = stock_data_list[i:i + batch_size]

                try:
                    self._safe_batch_update(batch, update_fields)
                    total_updated += len(batch)
                    print(f"已更新 {total_updated}/{len(stock_data_list)} 条数据")

                except Exception as e:
                    print(f"第 {i // batch_size + 1} 批更新失败: {e}")

            print(f"PE/PB数据更新完成，共成功更新 {total_updated} 条数据")

        except Exception as e:
            print(f"更新PE/PB数据时发生严重错误: {e}")
            raise e

    def _safe_batch_update(self, batch_data, update_fields):
        """安全的批量更新方法"""
        try:
            if hasattr(mapper, 'batch_update_by_ts_code_and_trade_date'):
                mapper.batch_update_by_ts_code_and_trade_date(batch_data, update_fields)
            else:
                for stock_data in batch_data:
                    mapper.update_by_ts_code_and_trade_date(stock_data, update_fields)

        except Exception as e:
            print(f"批量更新失败，尝试单条更新: {e}")

            success_count = 0
            for i, stock_data in enumerate(batch_data):
                try:
                    mapper.update_by_ts_code_and_trade_date(stock_data, update_fields)
                    success_count += 1
                except Exception as single_error:
                    print(f"  单条更新失败 [{i + 1}/{len(batch_data)}] - "
                          f"代码: {stock_data.ts_code}, 日期: {stock_data.trade_date}, "
                          f"错误: {single_error}")

            if success_count < len(batch_data):
                print(f"  批次处理完成，成功: {success_count}, 失败: {len(batch_data) - success_count}")
