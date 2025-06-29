# 自动同步数据
from datetime import datetime, timedelta

from entity import constant
from entity.stock_weight import StockWeight
from mysql_connect.stock_weight_mapper import StockWeightMapper
from tu_share_factory.tu_share_factory import TuShareFactory
from util.date_util import TimeUtils

mapper = StockWeightMapper()

def additional_data():
    for ts_code in constant.TS_CODE_LIST:
        if (ts_code == '000001.SH'):
            continue

        history_start_date = constant.HISTORY_START_DATE_MAP[ts_code]
        max_trade_datetime = mapper.get_max_trade_time(ts_code)
        if max_trade_datetime is None:
            max_trade_date = history_start_date
        else:
            max_trade_date = max_trade_datetime
        start_date = TimeUtils.get_n_days_before_or_after(max_trade_date, 1, True)
        sync_stock_weight(ts_code, start_date, TimeUtils.get_current_date_str())

def sync_stock_weight(index_code, start_date, end_date):
    pro = TuShareFactory.build_api_client()
    # 将日期字符串转换为datetime对象
    start_date = datetime.strptime(start_date, '%Y%m%d')
    end_date = datetime.strptime(end_date, '%Y%m%d')

    # 循环遍历每个月
    current_month_start = start_date
    while current_month_start <= end_date:
        # 计算当前月份的结束日期
        next_month_start = (current_month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        current_month_end = next_month_start - timedelta(days=1)

        # 获取当前月份的指数成分股及其权重
        stock_info = pro.index_weight(index_code=index_code, start_date=current_month_start.strftime('%Y%m%d'),
                                      end_date=current_month_end.strftime('%Y%m%d'))

        # 去重并存储
        month_stock_info = stock_info.drop_duplicates(subset='con_code', keep='first')
        for _, row in month_stock_info.iterrows():
            # 生成数据
            stock_data = StockWeight(id=None,
                                     index_code=row['index_code'],
                                     trade_date=row['trade_date'],
                                     con_code=row['con_code'],
                                     weight=row['weight'])
            mapper.insert_index(stock_data)
        # 移动到下一个月
        current_month_start = next_month_start