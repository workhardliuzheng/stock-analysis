import numpy as np

from entity import constant
from entity.fund_data import FundData
from mysql_connect.fund_data_mapper import FundDataMapper
from mysql_connect.fund_mapper import FundMapper
from tu_share_factory.tu_share_factory import TuShareFactory
from util.date_util import TimeUtils

FUND_DATA_FIELDS = [
    "ts_code",
    "trade_date",
    "pre_close",
    "open",
    "high",
    "low",
    "close",
    "change",
    "pct_chg",
    "vol",
    "amount"
]
LIMIT = 1000
fund_data_mapper = FundDataMapper()
fund_mapper = FundMapper()


def additional_data():
    fund_map = constant.FUND_NAME_MAP
    for ts_code in fund_map.keys():
        found_date = fund_mapper.get_found_date(ts_code)
        min_date = fund_data_mapper.get_min_trade_time(ts_code)

        if min_date:
            start_date = TimeUtils.date_to_str(found_date)
            end_date = TimeUtils.date_to_str(min_date)
        else:
            start_date = TimeUtils.date_to_str(found_date)
            end_date = TimeUtils.get_current_date_str()

        sync_fund_data(ts_code, start_date, end_date, fund_map[ts_code])

def sync_fund_data(ts_code, start_date, end_date, name):
    pro = TuShareFactory.build_api_client()
    size = 1000
    index = 0

    while size >= 1000:
        daily_data = pro.fund_daily(**{
            "ts_code": ts_code,
            "start_date": start_date,
            "end_date": end_date,
            "limit": LIMIT,
            "offset": index * size
        }, fields=FUND_DATA_FIELDS)

        for data in daily_data.itertuples():
            # 生成数据
            fund_data = FundData(id=None,
                                     ts_code=data.ts_code,
                                     trade_date=TimeUtils.str_to_date(data.trade_date),
                                     name=name,
                                     pre_close= None if np.isnan(data.pre_close) else data.pre_close,
                                     open=None if np.isnan(data.open) else data.open,
                                     high=None if np.isnan(data.high) else data.high,
                                     low=None if np.isnan(data.low) else data.low,
                                     close=None if np.isnan(data.close) else data.close,
                                     change=None if np.isnan(data.change) else data.change,
                                     pct_chg=None if np.isnan(data.pct_chg) else data.pct_chg,
                                     vol=None if np.isnan(data.vol) else data.vol,
                                     amount=None if np.isnan(data.amount) else data.amount
                                     )
            fund_data_mapper.insert_fund_data(fund_data)
        index = index + 1
        size = daily_data.shape[0]