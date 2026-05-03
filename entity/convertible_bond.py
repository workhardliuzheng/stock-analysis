"""
可转债数据实体

提供 ConvertibleBondBasic (cb_basic) 和 ConvertibleBondDaily (cb_daily) 两个实体类
供 sync/sync_convertible.py 使用，通过 CommonMapper 完成数据库操作。
"""

from entity.base_entity import BaseEntity


class ConvertibleBondBasic(BaseEntity):
    """
    可转债基本信息 (对应表 cb_basic)

    来自 Tushare cb_basic 接口
    """

    def __init__(self, id=None, ts_code=None, bond_short_name=None,
                 stk_code=None, stk_short_name=None,
                 value_date=None, maturity_date=None,
                 issue_size=None, remain_size=None,
                 conv_start_date=None, conv_end_date=None,
                 conv_price=None, list_date=None, delist_date=None,
                 exchange=None, rate_type=None, coupon_rate=None):
        self.id = id
        self.ts_code = ts_code
        self.bond_short_name = bond_short_name
        self.stk_code = stk_code
        self.stk_short_name = stk_short_name
        self.value_date = value_date
        self.maturity_date = maturity_date
        self.issue_size = issue_size
        self.remain_size = remain_size
        self.conv_start_date = conv_start_date
        self.conv_end_date = conv_end_date
        self.conv_price = conv_price
        self.list_date = list_date
        self.delist_date = delist_date
        self.exchange = exchange
        self.rate_type = rate_type
        self.coupon_rate = coupon_rate

    def get_ts_code(self):
        return self.ts_code

    def set_id(self, id_):
        self.id = id_


class ConvertibleBondDaily(BaseEntity):
    """
    可转债日线行情 (对应表 cb_daily)

    来自 Tushare cb_daily 接口
    """

    def __init__(self, id=None, ts_code=None, trade_date=None,
                 open=None, high=None, low=None, close=None,
                 pre_close=None, change=None, pct_chg=None,
                 vol=None, amount=None):
        self.id = id
        self.ts_code = ts_code
        self.trade_date = trade_date
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.pre_close = pre_close
        self.change = change
        self.pct_chg = pct_chg
        self.vol = vol
        self.amount = amount

    def get_ts_code(self):
        return self.ts_code

    def get_trade_date(self):
        return self.trade_date

    def set_id(self, id_):
        self.id = id_
