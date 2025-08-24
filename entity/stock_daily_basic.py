from entity.base_entity import BaseEntity


class StockDailyBasic(BaseEntity):
    def __init__(self, id=None, ts_code=None, trade_date=None, close=None,
                 turnover_rate=None, turnover_rate_f=None, volume_ratio=None,
                 pe=None, pe_ttm=None, pb=None, ps=None, ps_ttm=None,
                 dv_ratio=None, dv_ttm=None, total_share=None, float_share=None,
                 free_share=None, total_mv=None, circ_mv=None, pe_profit_dedt=None, pe_ttm_profit_dedt=None):
        self.id = id
        self.ts_code = ts_code
        self.trade_date = trade_date
        self.close = close
        self.turnover_rate = turnover_rate
        self.turnover_rate_f = turnover_rate_f
        self.volume_ratio = volume_ratio
        self.pe = pe
        self.pe_ttm = pe_ttm
        self.pb = pb
        self.ps = ps
        self.ps_ttm = ps_ttm
        self.dv_ratio = dv_ratio
        self.dv_ttm = dv_ttm
        self.total_share = total_share
        self.float_share = float_share
        self.free_share = free_share
        self.total_mv = total_mv
        self.circ_mv = circ_mv
        self.pe_profit_dedt = pe_profit_dedt
        self.pe_ttm_profit_dedt = pe_ttm_profit_dedt

    # Getter方法
    def get_id(self):
        return self.id

    def get_ts_code(self):
        return self.ts_code

    def get_trade_date(self):
        return self.trade_date

    def get_close(self):
        return self.close

    def get_turnover_rate(self):
        return self.turnover_rate

    def get_turnover_rate_f(self):
        return self.turnover_rate_f

    def get_volume_ratio(self):
        return self.volume_ratio

    def get_pe(self):
        return self.pe

    def get_pe_ttm(self):
        return self.pe_ttm

    def get_pb(self):
        return self.pb

    def get_ps(self):
        return self.ps

    def get_ps_ttm(self):
        return self.ps_ttm

    def get_dv_ratio(self):
        return self.dv_ratio

    def get_dv_ttm(self):
        return self.dv_ttm

    def get_total_share(self):
        return self.total_share

    def get_float_share(self):
        return self.float_share

    def get_free_share(self):
        return self.free_share

    def get_total_mv(self):
        return self.total_mv

    def get_circ_mv(self):
        return self.circ_mv

    # Setter方法
    def set_id(self, id):
        self.id = id

    def set_ts_code(self, ts_code):
        self.ts_code = ts_code

    def set_trade_date(self, trade_date):
        self.trade_date = trade_date

    def set_close(self, close):
        self.close = close

    def set_turnover_rate(self, turnover_rate):
        self.turnover_rate = turnover_rate

    def set_turnover_rate_f(self, turnover_rate_f):
        self.turnover_rate_f = turnover_rate_f

    def set_volume_ratio(self, volume_ratio):
        self.volume_ratio = volume_ratio

    def set_pe(self, pe):
        self.pe = pe

    def set_pe_ttm(self, pe_ttm):
        self.pe_ttm = pe_ttm

    def set_pb(self, pb):
        self.pb = pb

    def set_ps(self, ps):
        self.ps = ps

    def set_ps_ttm(self, ps_ttm):
        self.ps_ttm = ps_ttm

    def set_dv_ratio(self, dv_ratio):
        self.dv_ratio = dv_ratio

    def set_dv_ttm(self, dv_ttm):
        self.dv_ttm = dv_ttm

    def set_total_share(self, total_share):
        self.total_share = total_share

    def set_float_share(self, float_share):
        self.float_share = float_share

    def set_free_share(self, free_share):
        self.free_share = free_share

    def set_total_mv(self, total_mv):
        self.total_mv = total_mv

    def set_circ_mv(self, circ_mv):
        self.circ_mv = circ_mv

    def get_pe_profit_dedt(self):
        return self.pe_profit_dedt

    def get_pe_ttm_profit_dedt(self):
        return self.pe_ttm_profit_dedt