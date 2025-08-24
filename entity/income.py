from entity.base_entity import BaseEntity

class Income(BaseEntity):
    def __init__(self, id=None, ts_code=None, ann_date=None, f_ann_date=None,
                 end_date=None, report_type=None, comp_type=None, end_type=None,
                 basic_eps=None, diluted_eps=None, total_revenue=None, revenue=None,
                 int_income=None, prem_earned=None, comm_income=None,
                 n_commis_income=None, n_oth_income=None, n_oth_b_income=None,
                 prem_income=None, out_prem=None, une_prem_reser=None,
                 reins_income=None, n_sec_tb_income=None, n_sec_uw_income=None,
                 n_asset_mg_income=None, oth_b_income=None, fv_value_chg_gain=None,
                 invest_income=None, ass_invest_income=None, forex_gain=None,
                 total_cogs=None, oper_cost=None, int_exp=None, comm_exp=None,
                 biz_tax_surchg=None, sell_exp=None, admin_exp=None, fin_exp=None,
                 assets_impair_loss=None, prem_refund=None, compens_payout=None,
                 reser_insur_liab=None, div_payt=None, reins_exp=None, oper_exp=None,
                 compens_payout_refu=None, insur_reser_refu=None,
                 reins_cost_refund=None, other_bus_cost=None, operate_profit=None,
                 non_oper_income=None, non_oper_exp=None, nca_disploss=None,
                 total_profit=None, income_tax=None, n_income=None,
                 n_income_attr_p=None, minority_gain=None, oth_compr_income=None,
                 t_compr_income=None, compr_inc_attr_p=None,
                 compr_inc_attr_m_s=None, ebit=None, ebitda=None,
                 insurance_exp=None, undist_profit=None, distable_profit=None,
                 rd_exp=None, fin_exp_int_exp=None, fin_exp_int_inc=None,
                 transfer_surplus_rese=None, transfer_housing_imprest=None,
                 transfer_oth=None, adj_lossgain=None, withdra_legal_surplus=None,
                 withdra_legal_pubfund=None, withdra_biz_devfund=None,
                 withdra_rese_fund=None, withdra_oth_ersu=None, workers_welfare=None,
                 distr_profit_shrhder=None, prfshare_payable_dvd=None,
                 comshare_payable_dvd=None, capit_comstock_div=None,
                 net_after_nr_lp_correct=None, oth_income=None,
                 asset_disp_income=None, continued_net_profit=None,
                 end_net_profit=None, credit_impa_loss=None,
                 net_expo_hedging_benefits=None, oth_impair_loss_assets=None,
                 total_opcost=None, amodcost_fin_assets=None, update_flag=None):
        self.id = id
        self.ts_code = ts_code
        self.ann_date = ann_date
        self.f_ann_date = f_ann_date
        self.end_date = end_date
        self.report_type = report_type
        self.comp_type = comp_type
        self.end_type = end_type
        self.basic_eps = basic_eps
        self.diluted_eps = diluted_eps
        self.total_revenue = total_revenue
        self.revenue = revenue
        self.int_income = int_income
        self.prem_earned = prem_earned
        self.comm_income = comm_income
        self.n_commis_income = n_commis_income
        self.n_oth_income = n_oth_income
        self.n_oth_b_income = n_oth_b_income
        self.prem_income = prem_income
        self.out_prem = out_prem
        self.une_prem_reser = une_prem_reser
        self.reins_income = reins_income
        self.n_sec_tb_income = n_sec_tb_income
        self.n_sec_uw_income = n_sec_uw_income
        self.n_asset_mg_income = n_asset_mg_income
        self.oth_b_income = oth_b_income
        self.fv_value_chg_gain = fv_value_chg_gain
        self.invest_income = invest_income
        self.ass_invest_income = ass_invest_income
        self.forex_gain = forex_gain
        self.total_cogs = total_cogs
        self.oper_cost = oper_cost
        self.int_exp = int_exp
        self.comm_exp = comm_exp
        self.biz_tax_surchg = biz_tax_surchg
        self.sell_exp = sell_exp
        self.admin_exp = admin_exp
        self.fin_exp = fin_exp
        self.assets_impair_loss = assets_impair_loss
        self.prem_refund = prem_refund
        self.compens_payout = compens_payout
        self.reser_insur_liab = reser_insur_liab
        self.div_payt = div_payt
        self.reins_exp = reins_exp
        self.oper_exp = oper_exp
        self.compens_payout_refu = compens_payout_refu
        self.insur_reser_refu = insur_reser_refu
        self.reins_cost_refund = reins_cost_refund
        self.other_bus_cost = other_bus_cost
        self.operate_profit = operate_profit
        self.non_oper_income = non_oper_income
        self.non_oper_exp = non_oper_exp
        self.nca_disploss = nca_disploss
        self.total_profit = total_profit
        self.income_tax = income_tax
        self.n_income = n_income
        self.n_income_attr_p = n_income_attr_p
        self.minority_gain = minority_gain
        self.oth_compr_income = oth_compr_income
        self.t_compr_income = t_compr_income
        self.compr_inc_attr_p = compr_inc_attr_p
        self.compr_inc_attr_m_s = compr_inc_attr_m_s
        self.ebit = ebit
        self.ebitda = ebitda
        self.insurance_exp = insurance_exp
        self.undist_profit = undist_profit
        self.distable_profit = distable_profit
        self.rd_exp = rd_exp
        self.fin_exp_int_exp = fin_exp_int_exp
        self.fin_exp_int_inc = fin_exp_int_inc
        self.transfer_surplus_rese = transfer_surplus_rese
        self.transfer_housing_imprest = transfer_housing_imprest
        self.transfer_oth = transfer_oth
        self.adj_lossgain = adj_lossgain
        self.withdra_legal_surplus = withdra_legal_surplus
        self.withdra_legal_pubfund = withdra_legal_pubfund
        self.withdra_biz_devfund = withdra_biz_devfund
        self.withdra_rese_fund = withdra_rese_fund
        self.withdra_oth_ersu = withdra_oth_ersu
        self.workers_welfare = workers_welfare
        self.distr_profit_shrhder = distr_profit_shrhder
        self.prfshare_payable_dvd = prfshare_payable_dvd
        self.comshare_payable_dvd = comshare_payable_dvd
        self.capit_comstock_div = capit_comstock_div
        self.net_after_nr_lp_correct = net_after_nr_lp_correct
        self.oth_income = oth_income
        self.asset_disp_income = asset_disp_income
        self.continued_net_profit = continued_net_profit
        self.end_net_profit = end_net_profit
        self.credit_impa_loss = credit_impa_loss
        self.net_expo_hedging_benefits = net_expo_hedging_benefits
        self.oth_impair_loss_assets = oth_impair_loss_assets
        self.total_opcost = total_opcost
        self.amodcost_fin_assets = amodcost_fin_assets
        self.update_flag = update_flag

    # Getter methods for each field
    def get_ts_code(self):
        return self.ts_code

    def get_ann_date(self):
        return self.ann_date

    def get_f_ann_date(self):
        return self.f_ann_date

    def get_end_date(self):
        return self.end_date

    def get_report_type(self):
        return self.report_type

    def get_comp_type(self):
        return self.comp_type

    def get_end_type(self):
        return self.end_type

    def get_basic_eps(self):
        return self.basic_eps

    def get_diluted_eps(self):
        return self.diluted_eps

    def get_total_revenue(self):
        return self.total_revenue

    def get_revenue(self):
        return self.revenue

    def get_int_income(self):
        return self.int_income

    def get_prem_earned(self):
        return self.prem_earned

    def get_comm_income(self):
        return self.comm_income

    def get_n_commis_income(self):
        return self.n_commis_income

    def get_n_oth_income(self):
        return self.n_oth_income

    def get_n_oth_b_income(self):
        return self.n_oth_b_income

    def get_prem_income(self):
        return self.prem_income

    def get_out_prem(self):
        return self.out_prem

    def get_une_prem_reser(self):
        return self.une_prem_reser

    def get_reins_income(self):
        return self.reins_income

    def get_n_sec_tb_income(self):
        return self.n_sec_tb_income

    def get_n_sec_uw_income(self):
        return self.n_sec_uw_income

    def get_n_asset_mg_income(self):
        return self.n_asset_mg_income

    def get_oth_b_income(self):
        return self.oth_b_income

    def get_fv_value_chg_gain(self):
        return self.fv_value_chg_gain

    def get_invest_income(self):
        return self.invest_income

    def get_ass_invest_income(self):
        return self.ass_invest_income

    def get_forex_gain(self):
        return self.forex_gain

    def get_total_cogs(self):
        return self.total_cogs

    def get_oper_cost(self):
        return self.oper_cost

    def get_int_exp(self):
        return self.int_exp

    def get_comm_exp(self):
        return self.comm_exp

    def get_biz_tax_surchg(self):
        return self.biz_tax_surchg

    def get_sell_exp(self):
        return self.sell_exp

    def get_admin_exp(self):
        return self.admin_exp

    def get_fin_exp(self):
        return self.fin_exp

    def get_assets_impair_loss(self):
        return self.assets_impair_loss

    def get_prem_refund(self):
        return self.prem_refund

    def get_compens_payout(self):
        return self.compens_payout

    def get_reser_insur_liab(self):
        return self.reser_insur_liab

    def get_div_payt(self):
        return self.div_payt

    def get_reins_exp(self):
        return self.reins_exp

    def get_oper_exp(self):
        return self.oper_exp

    def get_compens_payout_refu(self):
        return self.compens_payout_refu

    def get_insur_reser_refu(self):
        return self.insur_reser_refu

    def get_reins_cost_refund(self):
        return self.reins_cost_refund

    def get_other_bus_cost(self):
        return self.other_bus_cost

    def get_operate_profit(self):
        return self.operate_profit

    def get_non_oper_income(self):
        return self.non_oper_income

    def get_non_oper_exp(self):
        return self.non_oper_exp

    def get_nca_disploss(self):
        return self.nca_disploss

    def get_total_profit(self):
        return self.total_profit

    def get_income_tax(self):
        return self.income_tax

    def get_n_income(self):
        return self.n_income

    def get_n_income_attr_p(self):
        return self.n_income_attr_p

    def get_minority_gain(self):
        return self.minority_gain

    def get_oth_compr_income(self):
        return self.oth_compr_income

    def get_t_compr_income(self):
        return self.t_compr_income

    def get_compr_inc_attr_p(self):
        return self.compr_inc_attr_p

    def get_compr_inc_attr_m_s(self):
        return self.compr_inc_attr_m_s

    def get_ebit(self):
        return self.ebit

    def get_ebitda(self):
        return self.ebitda

    def get_insurance_exp(self):
        return self.insurance_exp

    def get_undist_profit(self):
        return self.undist_profit

    def get_distable_profit(self):
        return self.distable_profit

    def get_rd_exp(self):
        return self.rd_exp

    def get_fin_exp_int_exp(self):
        return self.fin_exp_int_exp

    def get_fin_exp_int_inc(self):
        return self.fin_exp_int_inc

    def get_transfer_surplus_rese(self):
        return self.transfer_surplus_rese

    def get_transfer_housing_imprest(self):
        return self.transfer_housing_imprest

    def get_transfer_oth(self):
        return self.transfer_oth

    def get_adj_lossgain(self):
        return self.adj_lossgain

    def get_withdra_legal_surplus(self):
        return self.withdra_legal_surplus

    def get_withdra_legal_pubfund(self):
        return self.withdra_legal_pubfund

    def get_withdra_biz_devfund(self):
        return self.withdra_biz_devfund

    def get_withdra_rese_fund(self):
        return self.withdra_rese_fund

    def get_withdra_oth_ersu(self):
        return self.withdra_oth_ersu

    def get_workers_welfare(self):
        return self.workers_welfare

    def get_distr_profit_shrhder(self):
        return self.distr_profit_shrhder

    def get_prfshare_payable_dvd(self):
        return self.prfshare_payable_dvd

    def get_comshare_payable_dvd(self):
        return self.comshare_payable_dvd

    def get_capit_comstock_div(self):
        return self.capit_comstock_div

    def get_net_after_nr_lp_correct(self):
        return self.net_after_nr_lp_correct

    def get_asset_disp_income(self):
        return self.asset_disp_income

    def get_continued_net_profit(self):
        return self.continued_net_profit

    def get_end_net_profit(self):
        return self.end_net_profit

    def get_credit_impa_loss(self):
        return self.credit_impa_loss

    def get_net_expo_hedging_benefits(self):
        return self.net_expo_hedging_benefits

    def get_oth_impair_loss_assets(self):
        return self.oth_impair_loss_assets

    def get_total_opcost(self):
        return self.total_opcost

    def get_amodcost_fin_assets(self):
        return self.amodcost_fin_assets

    def get_update_flag(self):
        return self.update_flag

    # Setter method for id
    def set_id(self, id):
        self.id = id


