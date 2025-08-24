from entity.base_entity import BaseEntity

class FinancialData(BaseEntity):
    def __init__(self, id=None, ts_code=None, ann_date=None, end_date=None,
                 eps=None, dt_eps=None, total_revenue_ps=None, revenue_ps=None,
                 capital_rese_ps=None, surplus_rese_ps=None, undist_profit_ps=None,
                 extra_item=None, profit_dedt=None, gross_margin=None, current_ratio=None,
                 quick_ratio=None, cash_ratio=None, invturn_days=None, arturn_days=None,
                 inv_turn=None, ar_turn=None, ca_turn=None, fa_turn=None, assets_turn=None,
                 op_income=None, valuechange_income=None, interst_income=None, daa=None,
                 ebit=None, ebitda=None, fcff=None, fcfe=None, current_exint=None,
                 noncurrent_exint=None, interestdebt=None, netdebt=None, tangible_asset=None,
                 working_capital=None, networking_capital=None, invest_capital=None,
                 retained_earnings=None, diluted2_eps=None, bps=None, ocfps=None,
                 retainedps=None, cfps=None, ebit_ps=None, fcff_ps=None, fcfe_ps=None,
                 netprofit_margin=None, grossprofit_margin=None, cogs_of_sales=None,
                 expense_of_sales=None, profit_to_gr=None, saleexp_to_gr=None,
                 adminexp_of_gr=None, finaexp_of_gr=None, impai_ttm=None, gc_of_gr=None,
                 op_of_gr=None, ebit_of_gr=None, roe=None, roe_waa=None, roe_dt=None,
                 roa=None, npta=None, roic=None, roe_yearly=None, roa2_yearly=None,
                 roe_avg=None, opincome_of_ebt=None, investincome_of_ebt=None,
                 n_op_profit_of_ebt=None, tax_to_ebt=None, dtprofit_to_profit=None,
                 salescash_to_or=None, ocf_to_or=None, ocf_to_opincome=None,
                 capitalized_to_da=None, debt_to_assets=None, assets_to_eqt=None,
                 dp_assets_to_eqt=None, ca_to_assets=None, nca_to_assets=None,
                 tbassets_to_totalassets=None, int_to_talcap=None, eqt_to_talcapital=None,
                 currentdebt_to_debt=None, longdeb_to_debt=None, ocf_to_shortdebt=None,
                 debt_to_eqt=None, eqt_to_debt=None, eqt_to_interestdebt=None,
                 tangibleasset_to_debt=None, tangasset_to_intdebt=None,
                 tangibleasset_to_netdebt=None, ocf_to_debt=None, ocf_to_interestdebt=None,
                 ocf_to_netdebt=None, ebit_to_interest=None, longdebt_to_workingcapital=None,
                 ebitda_to_debt=None, turn_days=None, roa_yearly=None, roa_dp=None,
                 fixed_assets=None, profit_prefin_exp=None, non_op_profit=None,
                 op_to_ebt=None, nop_to_ebt=None, ocf_to_profit=None, cash_to_liqdebt=None,
                 cash_to_liqdebt_withinterest=None, op_to_liqdebt=None, op_to_debt=None,
                 roic_yearly=None, total_fa_trun=None, profit_to_op=None, q_opincome=None,
                 q_investincome=None, q_dtprofit=None, q_eps=None, q_netprofit_margin=None,
                 q_gsprofit_margin=None, q_exp_to_sales=None, q_profit_to_gr=None,
                 q_saleexp_to_gr=None, q_adminexp_to_gr=None, q_finaexp_to_gr=None,
                 q_impair_to_gr_ttm=None, q_gc_to_gr=None, q_op_to_gr=None, q_roe=None,
                 q_dt_roe=None, q_npta=None, q_opincome_to_ebt=None, q_investincome_to_ebt=None,
                 q_dtprofit_to_profit=None, q_salescash_to_or=None, q_ocf_to_sales=None,
                 q_ocf_to_or=None, basic_eps_yoy=None, dt_eps_yoy=None, cfps_yoy=None,
                 op_yoy=None, ebt_yoy=None, netprofit_yoy=None, dt_netprofit_yoy=None,
                 ocf_yoy=None, roe_yoy=None, bps_yoy=None, assets_yoy=None, eqt_yoy=None,
                 tr_yoy=None, or_yoy=None, q_gr_yoy=None, q_gr_qoq=None, q_sales_yoy=None,
                 q_sales_qoq=None, q_op_yoy=None, q_op_qoq=None, q_profit_yoy=None,
                 q_profit_qoq=None, q_netprofit_yoy=None, q_netprofit_qoq=None,
                 equity_yoy=None, rd_exp=None, update_flag=None):
        self.id = id
        self.ts_code = ts_code
        self.ann_date = ann_date
        self.end_date = end_date
        self.eps = eps
        self.dt_eps = dt_eps
        self.total_revenue_ps = total_revenue_ps
        self.revenue_ps = revenue_ps
        self.capital_rese_ps = capital_rese_ps
        self.surplus_rese_ps = surplus_rese_ps
        self.undist_profit_ps = undist_profit_ps
        self.extra_item = extra_item
        self.profit_dedt = profit_dedt
        self.gross_margin = gross_margin
        self.current_ratio = current_ratio
        self.quick_ratio = quick_ratio
        self.cash_ratio = cash_ratio
        self.invturn_days = invturn_days
        self.arturn_days = arturn_days
        self.inv_turn = inv_turn
        self.ar_turn = ar_turn
        self.ca_turn = ca_turn
        self.fa_turn = fa_turn
        self.assets_turn = assets_turn
        self.op_income = op_income
        self.valuechange_income = valuechange_income
        self.interst_income = interst_income
        self.daa = daa
        self.ebit = ebit
        self.ebitda = ebitda
        self.fcff = fcff
        self.fcfe = fcfe
        self.current_exint = current_exint
        self.noncurrent_exint = noncurrent_exint
        self.interestdebt = interestdebt
        self.netdebt = netdebt
        self.tangible_asset = tangible_asset
        self.working_capital = working_capital
        self.networking_capital = networking_capital
        self.invest_capital = invest_capital
        self.retained_earnings = retained_earnings
        self.diluted2_eps = diluted2_eps
        self.bps = bps
        self.ocfps = ocfps
        self.retainedps = retainedps
        self.cfps = cfps
        self.ebit_ps = ebit_ps
        self.fcff_ps = fcff_ps
        self.fcfe_ps = fcfe_ps
        self.netprofit_margin = netprofit_margin
        self.grossprofit_margin = grossprofit_margin
        self.cogs_of_sales = cogs_of_sales
        self.expense_of_sales = expense_of_sales
        self.profit_to_gr = profit_to_gr
        self.saleexp_to_gr = saleexp_to_gr
        self.adminexp_of_gr = adminexp_of_gr
        self.finaexp_of_gr = finaexp_of_gr
        self.impai_ttm = impai_ttm
        self.gc_of_gr = gc_of_gr
        self.op_of_gr = op_of_gr
        self.ebit_of_gr = ebit_of_gr
        self.roe = roe
        self.roe_waa = roe_waa
        self.roe_dt = roe_dt
        self.roa = roa
        self.npta = npta
        self.roic = roic
        self.roe_yearly = roe_yearly
        self.roa2_yearly = roa2_yearly
        self.roe_avg = roe_avg
        self.opincome_of_ebt = opincome_of_ebt
        self.investincome_of_ebt = investincome_of_ebt
        self.n_op_profit_of_ebt = n_op_profit_of_ebt
        self.tax_to_ebt = tax_to_ebt
        self.dtprofit_to_profit = dtprofit_to_profit
        self.salescash_to_or = salescash_to_or
        self.ocf_to_or = ocf_to_or
        self.ocf_to_opincome = ocf_to_opincome
        self.capitalized_to_da = capitalized_to_da
        self.debt_to_assets = debt_to_assets
        self.assets_to_eqt = assets_to_eqt
        self.dp_assets_to_eqt = dp_assets_to_eqt
        self.ca_to_assets = ca_to_assets
        self.nca_to_assets = nca_to_assets
        self.tbassets_to_totalassets = tbassets_to_totalassets
        self.int_to_talcap = int_to_talcap
        self.eqt_to_talcapital = eqt_to_talcapital
        self.currentdebt_to_debt = currentdebt_to_debt
        self.longdeb_to_debt = longdeb_to_debt
        self.ocf_to_shortdebt = ocf_to_shortdebt
        self.debt_to_eqt = debt_to_eqt
        self.eqt_to_debt = eqt_to_debt
        self.eqt_to_interestdebt = eqt_to_interestdebt
        self.tangibleasset_to_debt = tangibleasset_to_debt
        self.tangasset_to_intdebt = tangasset_to_intdebt
        self.tangibleasset_to_netdebt = tangibleasset_to_netdebt
        self.ocf_to_debt = ocf_to_debt
        self.ocf_to_interestdebt = ocf_to_interestdebt
        self.ocf_to_netdebt = ocf_to_netdebt
        self.ebit_to_interest = ebit_to_interest
        self.longdebt_to_workingcapital = longdebt_to_workingcapital
        self.ebitda_to_debt = ebitda_to_debt
        self.turn_days = turn_days
        self.roa_yearly = roa_yearly
        self.roa_dp = roa_dp
        self.fixed_assets = fixed_assets
        self.profit_prefin_exp = profit_prefin_exp
        self.non_op_profit = non_op_profit
        self.op_to_ebt = op_to_ebt
        self.nop_to_ebt = nop_to_ebt
        self.ocf_to_profit = ocf_to_profit
        self.cash_to_liqdebt = cash_to_liqdebt
        self.cash_to_liqdebt_withinterest = cash_to_liqdebt_withinterest
        self.op_to_liqdebt = op_to_liqdebt
        self.op_to_debt = op_to_debt
        self.roic_yearly = roic_yearly
        self.total_fa_trun = total_fa_trun
        self.profit_to_op = profit_to_op
        self.q_opincome = q_opincome
        self.q_investincome = q_investincome
        self.q_dtprofit = q_dtprofit
        self.q_eps = q_eps
        self.q_netprofit_margin = q_netprofit_margin
        self.q_gsprofit_margin = q_gsprofit_margin
        self.q_exp_to_sales = q_exp_to_sales
        self.q_profit_to_gr = q_profit_to_gr
        self.q_saleexp_to_gr = q_saleexp_to_gr
        self.q_adminexp_to_gr = q_adminexp_to_gr
        self.q_finaexp_to_gr = q_finaexp_to_gr
        self.q_impair_to_gr_ttm = q_impair_to_gr_ttm
        self.q_gc_to_gr = q_gc_to_gr
        self.q_op_to_gr = q_op_to_gr
        self.q_roe = q_roe
        self.q_dt_roe = q_dt_roe
        self.q_npta = q_npta
        self.q_opincome_to_ebt = q_opincome_to_ebt
        self.q_investincome_to_ebt = q_investincome_to_ebt
        self.q_dtprofit_to_profit = q_dtprofit_to_profit
        self.q_salescash_to_or = q_salescash_to_or
        self.q_ocf_to_sales = q_ocf_to_sales
        self.q_ocf_to_or = q_ocf_to_or
        self.basic_eps_yoy = basic_eps_yoy
        self.dt_eps_yoy = dt_eps_yoy
        self.cfps_yoy = cfps_yoy
        self.op_yoy = op_yoy
        self.ebt_yoy = ebt_yoy
        self.netprofit_yoy = netprofit_yoy
        self.dt_netprofit_yoy = dt_netprofit_yoy
        self.ocf_yoy = ocf_yoy
        self.roe_yoy = roe_yoy
        self.bps_yoy = bps_yoy
        self.assets_yoy = assets_yoy
        self.eqt_yoy = eqt_yoy
        self.tr_yoy = tr_yoy
        self.or_yoy = or_yoy
        self.q_gr_yoy = q_gr_yoy
        self.q_gr_qoq = q_gr_qoq
        self.q_sales_yoy = q_sales_yoy
        self.q_sales_qoq = q_sales_qoq
        self.q_op_yoy = q_op_yoy
        self.q_op_qoq = q_op_qoq
        self.q_profit_yoy = q_profit_yoy
        self.q_profit_qoq = q_profit_qoq
        self.q_netprofit_yoy = q_netprofit_yoy
        self.q_netprofit_qoq = q_netprofit_qoq
        self.equity_yoy = equity_yoy
        self.rd_exp = rd_exp
        self.update_flag = update_flag

    # Getter methods for each field
    def get_ts_code(self):
        return self.ts_code

    def get_ann_date(self):
        return self.ann_date

    def get_end_date(self):
        return self.end_date

    def get_eps(self):
        return self.eps

    def get_dt_eps(self):
        return self.dt_eps

    def get_total_revenue_ps(self):
        return self.total_revenue_ps

    def get_revenue_ps(self):
        return self.revenue_ps

    def get_capital_rese_ps(self):
        return self.capital_rese_ps

    def get_surplus_rese_ps(self):
        return self.surplus_rese_ps

    def get_undist_profit_ps(self):
        return self.undist_profit_ps

    def get_extra_item(self):
        return self.extra_item

    def get_profit_dedt(self):
        return self.profit_dedt

    def get_gross_margin(self):
        return self.gross_margin

    def get_current_ratio(self):
        return self.current_ratio

    def get_quick_ratio(self):
        return self.quick_ratio

    def get_cash_ratio(self):
        return self.cash_ratio

    def get_invturn_days(self):
        return self.invturn_days

    def get_arturn_days(self):
        return self.arturn_days

    def get_inv_turn(self):
        return self.inv_turn

    def get_ar_turn(self):
        return self.ar_turn

    def get_ca_turn(self):
        return self.ca_turn

    def get_fa_turn(self):
        return self.fa_turn

    def get_assets_turn(self):
        return self.assets_turn

    def get_op_income(self):
        return self.op_income

    def get_valuechange_income(self):
        return self.valuechange_income

    def get_interst_income(self):
        return self.interst_income

    def get_daa(self):
        return self.daa

    def get_ebit(self):
        return self.ebit

    def get_ebitda(self):
        return self.ebitda

    def get_fcff(self):
        return self.fcff

    def get_fcfe(self):
        return self.fcfe

    def get_current_exint(self):
        return self.current_exint

    def get_noncurrent_exint(self):
        return self.noncurrent_exint

    def get_interestdebt(self):
        return self.interestdebt

    def get_netdebt(self):
        return self.netdebt

    def get_tangible_asset(self):
        return self.tangible_asset

    def get_working_capital(self):
        return self.working_capital

    def get_networking_capital(self):
        return self.networking_capital

    def get_invest_capital(self):
        return self.invest_capital

    def get_retained_earnings(self):
        return self.retained_earnings

    def get_diluted2_eps(self):
        return self.diluted2_eps

    def get_bps(self):
        return self.bps

    def get_ocfps(self):
        return self.ocfps

    def get_retainedps(self):
        return self.retainedps

    def get_cfps(self):
        return self.cfps

    def get_ebit_ps(self):
        return self.ebit_ps

    def get_fcff_ps(self):
        return self.fcff_ps

    def get_fcfe_ps(self):
        return self.fcfe_ps

    def get_netprofit_margin(self):
        return self.netprofit_margin

    def get_grossprofit_margin(self):
        return self.grossprofit_margin

    def get_cogs_of_sales(self):
        return self.cogs_of_sales

    def get_expense_of_sales(self):
        return self.expense_of_sales

    def get_profit_to_gr(self):
        return self.profit_to_gr

    def get_saleexp_to_gr(self):
        return self.saleexp_to_gr

    def get_adminexp_of_gr(self):
        return self.adminexp_of_gr

    def get_finaexp_of_gr(self):
        return self.finaexp_of_gr

    def get_impai_ttm(self):
        return self.impai_ttm

    def get_gc_of_gr(self):
        return self.gc_of_gr

    def get_op_of_gr(self):
        return self.op_of_gr

    def get_ebit_of_gr(self):
        return self.ebit_of_gr

    def get_roe(self):
        return self.roe

    def get_roe_waa(self):
        return self.roe_waa

    def get_roe_dt(self):
        return self.roe_dt

    def get_roa(self):
        return self.roa

    def get_npta(self):
        return self.npta

    def get_roic(self):
        return self.roic

    def get_roe_yearly(self):
        return self.roe_yearly

    def get_roa2_yearly(self):
        return self.roa2_yearly

    def get_roe_avg(self):
        return self.roe_avg

    def get_opincome_of_ebt(self):
        return self.opincome_of_ebt

    def get_investincome_of_ebt(self):
        return self.investincome_of_ebt

    def get_n_op_profit_of_ebt(self):
        return self.n_op_profit_of_ebt

    def get_tax_to_ebt(self):
        return self.tax_to_ebt

    def get_dtprofit_to_profit(self):
        return self.dtprofit_to_profit

    def get_salescash_to_or(self):
        return self.salescash_to_or

    def get_ocf_to_or(self):
        return self.ocf_to_or

    def get_ocf_to_opincome(self):
        return self.ocf_to_opincome

    def get_capitalized_to_da(self):
        return self.capitalized_to_da

    def get_debt_to_assets(self):
        return self.debt_to_assets

    def get_assets_to_eqt(self):
        return self.assets_to_eqt

    def get_dp_assets_to_eqt(self):
        return self.dp_assets_to_eqt

    def get_ca_to_assets(self):
        return self.ca_to_assets

    def get_nca_to_assets(self):
        return self.nca_to_assets

    def get_tbassets_to_totalassets(self):
        return self.tbassets_to_totalassets

    def get_int_to_talcap(self):
        return self.int_to_talcap

    def get_eqt_to_talcapital(self):
        return self.eqt_to_talcapital

    def get_currentdebt_to_debt(self):
        return self.currentdebt_to_debt

    def get_longdeb_to_debt(self):
        return self.longdeb_to_debt

    def get_ocf_to_shortdebt(self):
        return self.ocf_to_shortdebt

    def get_debt_to_eqt(self):
        return self.debt_to_eqt

    def get_eqt_to_debt(self):
        return self.eqt_to_debt

    def get_eqt_to_interestdebt(self):
        return self.eqt_to_interestdebt

    def get_tangibleasset_to_debt(self):
        return self.tangibleasset_to_debt

    def get_tangasset_to_intdebt(self):
        return self.tangasset_to_intdebt

    def get_tangibleasset_to_netdebt(self):
        return self.tangibleasset_to_netdebt

    def get_ocf_to_debt(self):
        return self.ocf_to_debt

    def get_ocf_to_interestdebt(self):
        return self.ocf_to_interestdebt

    def get_ocf_to_netdebt(self):
        return self.ocf_to_netdebt

    def get_ebit_to_interest(self):
        return self.ebit_to_interest

    def get_longdebt_to_workingcapital(self):
        return self.longdebt_to_workingcapital

    def get_ebitda_to_debt(self):
        return self.ebitda_to_debt

    def get_turn_days(self):
        return self.turn_days

    def get_roa_yearly(self):
        return self.roa_yearly

    def get_roa_dp(self):
        return self.roa_dp

    def get_fixed_assets(self):
        return self.fixed_assets

    def get_profit_prefin_exp(self):
        return self.profit_prefin_exp

    def get_non_op_profit(self):
        return self.non_op_profit

    def get_op_to_ebt(self):
        return self.op_to_ebt

    def get_nop_to_ebt(self):
        return self.nop_to_ebt

    def get_ocf_to_profit(self):
        return self.ocf_to_profit

    def get_cash_to_liqdebt(self):
        return self.cash_to_liqdebt

    def get_cash_to_liqdebt_withinterest(self):
        return self.cash_to_liqdebt_withinterest

    def get_op_to_liqdebt(self):
        return self.op_to_liqdebt

    def get_op_to_debt(self):
        return self.op_to_debt

    def get_roic_yearly(self):
        return self.roic_yearly

    def get_total_fa_trun(self):
        return self.total_fa_trun

    def get_profit_to_op(self):
        return self.profit_to_op

    def get_q_opincome(self):
        return self.q_opincome

    def get_q_investincome(self):
        return self.q_investincome

    def get_q_dtprofit(self):
        return self.q_dtprofit

    def get_q_eps(self):
        return self.q_eps

    def get_q_netprofit_margin(self):
        return self.q_netprofit_margin

    def get_q_gsprofit_margin(self):
        return self.q_gsprofit_margin

    def get_q_exp_to_sales(self):
        return self.q_exp_to_sales

    def get_q_profit_to_gr(self):
        return self.q_profit_to_gr

    def get_q_saleexp_to_gr(self):
        return self.q_saleexp_to_gr

    def get_q_adminexp_to_gr(self):
        return self.q_adminexp_to_gr

    def get_q_finaexp_to_gr(self):
        return self.q_finaexp_to_gr

    def get_q_impair_to_gr_ttm(self):
        return self.q_impair_to_gr_ttm

    def get_q_gc_to_gr(self):
        return self.q_gc_to_gr

    def get_q_op_to_gr(self):
        return self.q_op_to_gr

    def get_q_roe(self):
        return self.q_roe

    def get_q_dt_roe(self):
        return self.q_dt_roe

    def get_q_npta(self):
        return self.q_npta

    def get_q_opincome_to_ebt(self):
        return self.q_opincome_to_ebt

    def get_q_investincome_to_ebt(self):
        return self.q_investincome_to_ebt

    def get_q_dtprofit_to_profit(self):
        return self.q_dtprofit_to_profit

    def get_q_salescash_to_or(self):
        return self.q_salescash_to_or

    def get_q_ocf_to_sales(self):
        return self.q_ocf_to_sales

    def get_q_ocf_to_or(self):
        return self.q_ocf_to_or

    def get_basic_eps_yoy(self):
        return self.basic_eps_yoy

    def get_dt_eps_yoy(self):
        return self.dt_eps_yoy

    def get_cfps_yoy(self):
        return self.cfps_yoy

    def get_op_yoy(self):
        return self.op_yoy

    def get_ebt_yoy(self):
        return self.ebt_yoy

    def get_netprofit_yoy(self):
        return self.netprofit_yoy

    def get_dt_netprofit_yoy(self):
        return self.dt_netprofit_yoy

    def get_ocf_yoy(self):
        return self.ocf_yoy

    def get_roe_yoy(self):
        return self.roe_yoy

    def get_bps_yoy(self):
        return self.bps_yoy

    def get_assets_yoy(self):
        return self.assets_yoy

    def get_eqt_yoy(self):
        return self.eqt_yoy

    def get_tr_yoy(self):
        return self.tr_yoy

    def get_or_yoy(self):
        return self.or_yoy

    def get_q_gr_yoy(self):
        return self.q_gr_yoy

    def get_q_gr_qoq(self):
        return self.q_gr_qoq

    def get_q_sales_yoy(self):
        return self.q_sales_yoy

    def get_q_sales_qoq(self):
        return self.q_sales_qoq

    def get_q_op_yoy(self):
        return self.q_op_yoy

    def get_q_op_qoq(self):
        return self.q_op_qoq

    def get_q_profit_yoy(self):
        return self.q_profit_yoy

    def get_q_profit_qoq(self):
        return self.q_profit_qoq

    def get_q_netprofit_yoy(self):
        return self.q_netprofit_yoy

    def get_q_netprofit_qoq(self):
        return self.q_netprofit_qoq

    def get_equity_yoy(self):
        return self.equity_yoy

    def get_rd_exp(self):
        return self.rd_exp

    def get_update_flag(self):
        return self.update_flag

    # Setter method for id
    def set_id(self, id):
        self.id = id