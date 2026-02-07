"""
收入数据 ORM 模型
"""
from sqlalchemy import Column, Integer, String, Float
from mysql_connect.db import Base


class Income(Base):
    """利润表数据"""
    __tablename__ = 'income'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), index=True)
    ann_date = Column(String(10))
    f_ann_date = Column(String(10))
    end_date = Column(String(10), index=True)
    report_type = Column(String(10))
    comp_type = Column(String(10))
    end_type = Column(String(10))
    basic_eps = Column(Float)
    diluted_eps = Column(Float)
    total_revenue = Column(Float)
    revenue = Column(Float)
    int_income = Column(Float)
    prem_earned = Column(Float)
    comm_income = Column(Float)
    n_commis_income = Column(Float)
    n_oth_income = Column(Float)
    n_oth_b_income = Column(Float)
    prem_income = Column(Float)
    out_prem = Column(Float)
    une_prem_reser = Column(Float)
    reins_income = Column(Float)
    n_sec_tb_income = Column(Float)
    n_sec_uw_income = Column(Float)
    n_asset_mg_income = Column(Float)
    oth_b_income = Column(Float)
    fv_value_chg_gain = Column(Float)
    invest_income = Column(Float)
    ass_invest_income = Column(Float)
    forex_gain = Column(Float)
    total_cogs = Column(Float)
    oper_cost = Column(Float)
    int_exp = Column(Float)
    comm_exp = Column(Float)
    biz_tax_surchg = Column(Float)
    sell_exp = Column(Float)
    admin_exp = Column(Float)
    fin_exp = Column(Float)
    assets_impair_loss = Column(Float)
    prem_refund = Column(Float)
    compens_payout = Column(Float)
    reser_insur_liab = Column(Float)
    div_payt = Column(Float)
    reins_exp = Column(Float)
    oper_exp = Column(Float)
    compens_payout_refu = Column(Float)
    insur_reser_refu = Column(Float)
    reins_cost_refund = Column(Float)
    other_bus_cost = Column(Float)
    operate_profit = Column(Float)
    non_oper_income = Column(Float)
    non_oper_exp = Column(Float)
    nca_disploss = Column(Float)
    total_profit = Column(Float)
    income_tax = Column(Float)
    n_income = Column(Float)
    n_income_attr_p = Column(Float)
    minority_gain = Column(Float)
    oth_compr_income = Column(Float)
    t_compr_income = Column(Float)
    compr_inc_attr_p = Column(Float)
    compr_inc_attr_m_s = Column(Float)
    ebit = Column(Float)
    ebitda = Column(Float)
    insurance_exp = Column(Float)
    undist_profit = Column(Float)
    distable_profit = Column(Float)
    rd_exp = Column(Float)
    fin_exp_int_exp = Column(Float)
    fin_exp_int_inc = Column(Float)
    transfer_surplus_rese = Column(Float)
    transfer_housing_imprest = Column(Float)
    transfer_oth = Column(Float)
    adj_lossgain = Column(Float)
    withdra_legal_surplus = Column(Float)
    withdra_legal_pubfund = Column(Float)
    withdra_biz_devfund = Column(Float)
    withdra_rese_fund = Column(Float)
    withdra_oth_ersu = Column(Float)
    workers_welfare = Column(Float)
    distr_profit_shrhder = Column(Float)
    prfshare_payable_dvd = Column(Float)
    comshare_payable_dvd = Column(Float)
    capit_comstock_div = Column(Float)
    net_after_nr_lp_correct = Column(Float)
    oth_income = Column(Float)
    asset_disp_income = Column(Float)
    continued_net_profit = Column(Float)
    end_net_profit = Column(Float)
    credit_impa_loss = Column(Float)
    net_expo_hedging_benefits = Column(Float)
    oth_impair_loss_assets = Column(Float)
    total_opcost = Column(Float)
    amodcost_fin_assets = Column(Float)
    update_flag = Column(String(5))
    
    # 常用 getter 方法
    def get_ts_code(self):
        return self.ts_code
    
    def get_ann_date(self):
        return self.ann_date
    
    def get_end_date(self):
        return self.end_date
    
    def get_total_revenue(self):
        return self.total_revenue
    
    def get_n_income(self):
        return self.n_income
    
    def set_id(self, id):
        self.id = id
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    def to_dict_with_backticks(self, contains_id=True):
        data_dict = self.to_dict()
        if not contains_id:
            data_dict.pop('id', None)
        return {f'`{key}`': value for key, value in sorted(data_dict.items())}
