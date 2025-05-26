from PIL.ImageChops import offset

from entity import constant
from entity.market_data import MarketData
from mysql_connect.market_data_mapper import MarketDataMapper
from tu_share_factory.tu_share_factory import TuShareFactory
from util.date_util import TimeUtils

MARKET_DATA_FIELDS=["trade_date", "ts_code", "ts_name", "total_mv", "vol", "trans_count", "pe",
    "tr", "exchange", "amount"]
LIMIT = 1000
mapper = MarketDataMapper()


def additional_data():
    history_start_date = '20150101'
    min_trade_datetime = mapper.get_min_trade_time()
    if min_trade_datetime is None:
        min_trade_datetime = history_start_date
    else:
        min_trade_datetime = TimeUtils.date_to_str(min_trade_datetime)
    sync_market_date(min_trade_datetime, TimeUtils.get_current_date_str())

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
                                     ts_code=data['ts_code'],
                                     trade_date=data['trade_date'],
                                     ts_name=data['ts_name'],
                                     total_mv=data['total_mv'],
                                     vol=data['vol'],
                                     trans_count=data['trans_count'],
                                     pe=data['pe'],
                                     tr=data['tr'],
                                     exchange=data['exchange'],
                                     amount=data['amount'],
                                     )
            mapper.insert_market_data(market_data)