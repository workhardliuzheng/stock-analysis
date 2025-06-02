import numpy as np
from PIL.ImageChops import offset

from entity import constant
from entity.market_data import MarketData
from mysql_connect.market_data_mapper import MarketDataMapper
from tu_share_factory.tu_share_factory import TuShareFactory
from util.date_util import TimeUtils

MARKET_DATA_FIELDS=["trade_date", "ts_code", "ts_name", "total_mv", "vol", "trans_count", "pe",
    "tr", "exchange", "amount", "com_count", "total_share", "float_share", "float_mv"]
LIMIT = 1000
mapper = MarketDataMapper()


def additional_data():
    history_start_date = '20150101'
    min_trade_datetime = mapper.get_min_trade_time()
    if min_trade_datetime is None:
        min_trade_datetime = TimeUtils.get_current_date_str()
    else:
        min_trade_datetime = TimeUtils.date_to_str(min_trade_datetime)
    sync_market_date(history_start_date, min_trade_datetime)

def sync_market_date(start_date, end_date):
    pro = TuShareFactory.build_api_client()
    size = 1000
    index = 0

    while size >= 1000:
        daily_data = pro.daily_info(**{
            "start_date": start_date,
            "end_date": end_date,
            "limit": LIMIT,
            "offset": index * size
        }, fields=MARKET_DATA_FIELDS)

        for data in daily_data.itertuples():
            # 生成数据
            market_data = MarketData(id=None,
                                     ts_code=data.ts_code,
                                     trade_date=TimeUtils.str_to_date(data.trade_date),
                                     ts_name=data.ts_name,
                                     total_mv= None if np.isnan(data.total_mv) else data.total_mv,
                                     vol=None if np.isnan(data.vol) else data.vol,
                                     trans_count=None if np.isnan(data.trans_count) else data.trans_count,
                                     pe=None if np.isnan(data.pe) else data.pe,
                                     tr=None if np.isnan(data.tr) else data.tr,
                                     exchange=data.exchange,
                                     amount=None if np.isnan(data.amount) else data.amount,
                                     float_mv=None if np.isnan(data.float_mv) else data.float_mv,
                                     float_share=None if np.isnan(data.float_share) else data.float_share,
                                     total_share=None if np.isnan(data.total_share) else data.total_share,
                                     com_count=None if np.isnan(data.com_count) else data.com_count,
                                     )
            mapper.insert_market_data(market_data)
        index = index + 1