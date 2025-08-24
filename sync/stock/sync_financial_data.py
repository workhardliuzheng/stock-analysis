# 自动同步数据
import time
from datetime import datetime, timedelta
import pandas as pd

from entity import constant
from entity.financial_data import FinancialData
from mysql_connect.financial_data_mapper import FinancialDataMapper
from mysql_connect.stock_basic_mapper import StockBasicMapper
from tu_share_factory.tu_share_factory import TuShareFactory
from util.date_util import TimeUtils

mapper = FinancialDataMapper()
stock_basic_mapper = StockBasicMapper()
FINANCIAL_DATA_FIELDS = ["ts_code", "ann_date", "end_date", "eps", "dt_eps", "total_revenue_ps", "revenue_ps",
                         "capital_rese_ps", "surplus_rese_ps", "undist_profit_ps", "extra_item", "profit_dedt",
                         "gross_margin", "current_ratio", "quick_ratio", "cash_ratio", "ar_turn", "ca_turn", "fa_turn",
                         "assets_turn", "op_income", "ebit", "ebitda", "fcff", "fcfe", "current_exint",
                         "noncurrent_exint", "interestdebt", "netdebt", "tangible_asset", "working_capital",
                         "networking_capital", "invest_capital", "retained_earnings", "diluted2_eps", "bps", "ocfps",
                         "retainedps", "cfps", "ebit_ps", "fcff_ps", "fcfe_ps", "netprofit_margin",
                         "grossprofit_margin", "cogs_of_sales", "expense_of_sales", "profit_to_gr", "saleexp_to_gr",
                         "adminexp_of_gr", "finaexp_of_gr", "impai_ttm", "gc_of_gr", "op_of_gr", "ebit_of_gr", "roe",
                         "roe_waa", "roe_dt", "roa", "npta", "roic", "roe_yearly", "roa2_yearly", "debt_to_assets",
                         "assets_to_eqt", "dp_assets_to_eqt", "ca_to_assets", "nca_to_assets",
                         "tbassets_to_totalassets", "int_to_talcap", "eqt_to_talcapital", "currentdebt_to_debt",
                         "longdeb_to_debt", "ocf_to_shortdebt", "debt_to_eqt", "eqt_to_debt", "eqt_to_interestdebt",
                         "tangibleasset_to_debt", "tangasset_to_intdebt", "tangibleasset_to_netdebt", "ocf_to_debt",
                         "turn_days", "roa_yearly", "roa_dp", "fixed_assets", "profit_to_op", "q_saleexp_to_gr",
                         "q_gc_to_gr", "q_roe", "q_dt_roe", "q_npta", "q_ocf_to_sales", "basic_eps_yoy", "dt_eps_yoy",
                         "cfps_yoy", "op_yoy", "ebt_yoy", "netprofit_yoy", "dt_netprofit_yoy", "ocf_yoy", "roe_yoy",
                         "bps_yoy", "assets_yoy", "eqt_yoy", "tr_yoy", "or_yoy", "q_sales_yoy", "q_op_qoq",
                         "equity_yoy", "invturn_days", "arturn_days", "inv_turn", "valuechange_income",
                         "interst_income", "daa", "roe_avg", "opincome_of_ebt", "investincome_of_ebt",
                         "n_op_profit_of_ebt", "tax_to_ebt", "dtprofit_to_profit", "salescash_to_or", "ocf_to_or",
                         "ocf_to_opincome", "capitalized_to_da", "ocf_to_interestdebt", "ocf_to_netdebt",
                         "ebit_to_interest", "longdebt_to_workingcapital", "ebitda_to_debt", "profit_prefin_exp",
                         "non_op_profit", "op_to_ebt", "nop_to_ebt", "ocf_to_profit", "cash_to_liqdebt",
                         "cash_to_liqdebt_withinterest", "op_to_liqdebt", "op_to_debt", "roic_yearly", "total_fa_trun",
                         "q_opincome", "q_investincome", "q_dtprofit", "q_eps", "q_netprofit_margin",
                         "q_gsprofit_margin", "q_exp_to_sales", "q_profit_to_gr", "q_adminexp_to_gr", "q_finaexp_to_gr",
                         "q_impair_to_gr_ttm", "q_op_to_gr", "q_opincome_to_ebt", "q_investincome_to_ebt",
                         "q_dtprofit_to_profit", "q_salescash_to_or", "q_ocf_to_or", "q_gr_yoy", "q_gr_qoq",
                         "q_sales_qoq", "q_op_yoy", "q_profit_yoy", "q_profit_qoq", "q_netprofit_yoy",
                         "q_netprofit_qoq", "rd_exp", "update_flag"]


def additional_data():
    ts_code_list = stock_basic_mapper.get_all_ts_codes()

    for ts_code in ts_code_list:
        start_date = mapper.get_max_end_date(ts_code=ts_code)
        start_date = start_date if start_date else '19000101'
        time.sleep(0.3)
        try:
            sync_financial_data(ts_code, start_date, TimeUtils.get_current_date_str())
        except Exception as e:
            print(f'插入股票{ts_code} 财务数据失败: {e}')
            time.sleep(30)
            sync_financial_data(ts_code, start_date, TimeUtils.get_current_date_str())


def sync_financial_data(ts_code, start_date, end_date):
    pro = TuShareFactory.build_api_client()

    # 批量大小
    BATCH_SIZE = 100

    financial_info = pro.fina_indicator(ts_code=ts_code, start_date=start_date,
                                        end_date=end_date, fields=FINANCIAL_DATA_FIELDS)

    # 准备批量数据
    batch_data = []
    total_count = 0

    for _, row in financial_info.iterrows():
        # 生成数据
        financial_data = FinancialData(
            id=None,
            ts_code=row['ts_code'] if pd.notna(row['ts_code']) else None,
            ann_date=row['ann_date'] if pd.notna(row['ann_date']) else None,
            end_date=row['end_date'] if pd.notna(row['end_date']) else None,
            eps=row['eps'] if pd.notna(row['eps']) else None,
            dt_eps=row['dt_eps'] if pd.notna(row['dt_eps']) else None,
            total_revenue_ps=row['total_revenue_ps'] if pd.notna(row['total_revenue_ps']) else None,
            revenue_ps=row['revenue_ps'] if pd.notna(row['revenue_ps']) else None,
            capital_rese_ps=row['capital_rese_ps'] if pd.notna(row['capital_rese_ps']) else None,
            surplus_rese_ps=row['surplus_rese_ps'] if pd.notna(row['surplus_rese_ps']) else None,
            undist_profit_ps=row['undist_profit_ps'] if pd.notna(row['undist_profit_ps']) else None,
            extra_item=row['extra_item'] if pd.notna(row['extra_item']) else None,
            profit_dedt=row['profit_dedt'] if pd.notna(row['profit_dedt']) else None,
            gross_margin=row['gross_margin'] if pd.notna(row['gross_margin']) else None,
            current_ratio=row['current_ratio'] if pd.notna(row['current_ratio']) else None,
            quick_ratio=row['quick_ratio'] if pd.notna(row['quick_ratio']) else None,
            cash_ratio=row['cash_ratio'] if pd.notna(row['cash_ratio']) else None,
            invturn_days=row['invturn_days'] if pd.notna(row['invturn_days']) else None,
            arturn_days=row['arturn_days'] if pd.notna(row['arturn_days']) else None,
            inv_turn=row['inv_turn'] if pd.notna(row['inv_turn']) else None,
            ar_turn=row['ar_turn'] if pd.notna(row['ar_turn']) else None,
            ca_turn=row['ca_turn'] if pd.notna(row['ca_turn']) else None,
            fa_turn=row['fa_turn'] if pd.notna(row['fa_turn']) else None,
            assets_turn=row['assets_turn'] if pd.notna(row['assets_turn']) else None,
            op_income=row['op_income'] if pd.notna(row['op_income']) else None,
            valuechange_income=row['valuechange_income'] if pd.notna(row['valuechange_income']) else None,
            interst_income=row['interst_income'] if pd.notna(row['interst_income']) else None,
            daa=row['daa'] if pd.notna(row['daa']) else None,
            ebit=row['ebit'] if pd.notna(row['ebit']) else None,
            ebitda=row['ebitda'] if pd.notna(row['ebitda']) else None,
            fcff=row['fcff'] if pd.notna(row['fcff']) else None,
            fcfe=row['fcfe'] if pd.notna(row['fcfe']) else None,
            current_exint=row['current_exint'] if pd.notna(row['current_exint']) else None,
            noncurrent_exint=row['noncurrent_exint'] if pd.notna(row['noncurrent_exint']) else None,
            interestdebt=row['interestdebt'] if pd.notna(row['interestdebt']) else None,
            netdebt=row['netdebt'] if pd.notna(row['netdebt']) else None,
            tangible_asset=row['tangible_asset'] if pd.notna(row['tangible_asset']) else None,
            working_capital=row['working_capital'] if pd.notna(row['working_capital']) else None,
            networking_capital=row['networking_capital'] if pd.notna(row['networking_capital']) else None,
            invest_capital=row['invest_capital'] if pd.notna(row['invest_capital']) else None,
            retained_earnings=row['retained_earnings'] if pd.notna(row['retained_earnings']) else None,
            diluted2_eps=row['diluted2_eps'] if pd.notna(row['diluted2_eps']) else None,
            bps=row['bps'] if pd.notna(row['bps']) else None,
            ocfps=row['ocfps'] if pd.notna(row['ocfps']) else None,
            retainedps=row['retainedps'] if pd.notna(row['retainedps']) else None,
            cfps=row['cfps'] if pd.notna(row['cfps']) else None,
            ebit_ps=row['ebit_ps'] if pd.notna(row['ebit_ps']) else None,
            fcff_ps=row['fcff_ps'] if pd.notna(row['fcff_ps']) else None,
            fcfe_ps=row['fcfe_ps'] if pd.notna(row['fcfe_ps']) else None,
            netprofit_margin=row['netprofit_margin'] if pd.notna(row['netprofit_margin']) else None,
            grossprofit_margin=row['grossprofit_margin'] if pd.notna(row['grossprofit_margin']) else None,
            cogs_of_sales=row['cogs_of_sales'] if pd.notna(row['cogs_of_sales']) else None,
            expense_of_sales=row['expense_of_sales'] if pd.notna(row['expense_of_sales']) else None,
            profit_to_gr=row['profit_to_gr'] if pd.notna(row['profit_to_gr']) else None,
            saleexp_to_gr=row['saleexp_to_gr'] if pd.notna(row['saleexp_to_gr']) else None,
            adminexp_of_gr=row['adminexp_of_gr'] if pd.notna(row['adminexp_of_gr']) else None,
            finaexp_of_gr=row['finaexp_of_gr'] if pd.notna(row['finaexp_of_gr']) else None,
            impai_ttm=row['impai_ttm'] if pd.notna(row['impai_ttm']) else None,
            gc_of_gr=row['gc_of_gr'] if pd.notna(row['gc_of_gr']) else None,
            op_of_gr=row['op_of_gr'] if pd.notna(row['op_of_gr']) else None,
            ebit_of_gr=row['ebit_of_gr'] if pd.notna(row['ebit_of_gr']) else None,
            roe=row['roe'] if pd.notna(row['roe']) else None,
            roe_waa=row['roe_waa'] if pd.notna(row['roe_waa']) else None,
            roe_dt=row['roe_dt'] if pd.notna(row['roe_dt']) else None,
            roa=row['roa'] if pd.notna(row['roa']) else None,
            npta=row['npta'] if pd.notna(row['npta']) else None,
            roic=row['roic'] if pd.notna(row['roic']) else None,
            roe_yearly=row['roe_yearly'] if pd.notna(row['roe_yearly']) else None,
            roa2_yearly=row['roa2_yearly'] if pd.notna(row['roa2_yearly']) else None,
            roe_avg=row['roe_avg'] if pd.notna(row['roe_avg']) else None,
            opincome_of_ebt=row['opincome_of_ebt'] if pd.notna(row['opincome_of_ebt']) else None,
            investincome_of_ebt=row['investincome_of_ebt'] if pd.notna(row['investincome_of_ebt']) else None,
            n_op_profit_of_ebt=row['n_op_profit_of_ebt'] if pd.notna(row['n_op_profit_of_ebt']) else None,
            tax_to_ebt=row['tax_to_ebt'] if pd.notna(row['tax_to_ebt']) else None,
            dtprofit_to_profit=row['dtprofit_to_profit'] if pd.notna(row['dtprofit_to_profit']) else None,
            salescash_to_or=row['salescash_to_or'] if pd.notna(row['salescash_to_or']) else None,
            ocf_to_or=row['ocf_to_or'] if pd.notna(row['ocf_to_or']) else None,
            ocf_to_opincome=row['ocf_to_opincome'] if pd.notna(row['ocf_to_opincome']) else None,
            capitalized_to_da=row['capitalized_to_da'] if pd.notna(row['capitalized_to_da']) else None,
            debt_to_assets=row['debt_to_assets'] if pd.notna(row['debt_to_assets']) else None,
            assets_to_eqt=row['assets_to_eqt'] if pd.notna(row['assets_to_eqt']) else None,
            dp_assets_to_eqt=row['dp_assets_to_eqt'] if pd.notna(row['dp_assets_to_eqt']) else None,
            ca_to_assets=row['ca_to_assets'] if pd.notna(row['ca_to_assets']) else None,
            nca_to_assets=row['nca_to_assets'] if pd.notna(row['nca_to_assets']) else None,
            tbassets_to_totalassets=row['tbassets_to_totalassets'] if pd.notna(
                row['tbassets_to_totalassets']) else None,
            int_to_talcap=row['int_to_talcap'] if pd.notna(row['int_to_talcap']) else None,
            eqt_to_talcapital=row['eqt_to_talcapital'] if pd.notna(row['eqt_to_talcapital']) else None,
            currentdebt_to_debt=row['currentdebt_to_debt'] if pd.notna(row['currentdebt_to_debt']) else None,
            longdeb_to_debt=row['longdeb_to_debt'] if pd.notna(row['longdeb_to_debt']) else None,
            ocf_to_shortdebt=row['ocf_to_shortdebt'] if pd.notna(row['ocf_to_shortdebt']) else None,
            debt_to_eqt=row['debt_to_eqt'] if pd.notna(row['debt_to_eqt']) else None,
            eqt_to_debt=row['eqt_to_debt'] if pd.notna(row['eqt_to_debt']) else None,
            eqt_to_interestdebt=row['eqt_to_interestdebt'] if pd.notna(row['eqt_to_interestdebt']) else None,
            tangibleasset_to_debt=row['tangibleasset_to_debt'] if pd.notna(row['tangibleasset_to_debt']) else None,
            tangasset_to_intdebt=row['tangasset_to_intdebt'] if pd.notna(row['tangasset_to_intdebt']) else None,
            tangibleasset_to_netdebt=row['tangibleasset_to_netdebt'] if pd.notna(
                row['tangibleasset_to_netdebt']) else None,
            ocf_to_debt=row['ocf_to_debt'] if pd.notna(row['ocf_to_debt']) else None,
            ocf_to_interestdebt=row['ocf_to_interestdebt'] if pd.notna(row['ocf_to_interestdebt']) else None,
            ocf_to_netdebt=row['ocf_to_netdebt'] if pd.notna(row['ocf_to_netdebt']) else None,
            ebit_to_interest=row['ebit_to_interest'] if pd.notna(row['ebit_to_interest']) else None,
            longdebt_to_workingcapital=row['longdebt_to_workingcapital'] if pd.notna(
                row['longdebt_to_workingcapital']) else None,
            ebitda_to_debt=row['ebitda_to_debt'] if pd.notna(row['ebitda_to_debt']) else None,
            turn_days=row['turn_days'] if pd.notna(row['turn_days']) else None,
            roa_yearly=row['roa_yearly'] if pd.notna(row['roa_yearly']) else None,
            roa_dp=row['roa_dp'] if pd.notna(row['roa_dp']) else None,
            fixed_assets=row['fixed_assets'] if pd.notna(row['fixed_assets']) else None,
            profit_prefin_exp=row['profit_prefin_exp'] if pd.notna(row['profit_prefin_exp']) else None,
            non_op_profit=row['non_op_profit'] if pd.notna(row['non_op_profit']) else None,
            op_to_ebt=row['op_to_ebt'] if pd.notna(row['op_to_ebt']) else None,
            nop_to_ebt=row['nop_to_ebt'] if pd.notna(row['nop_to_ebt']) else None,
            ocf_to_profit=row['ocf_to_profit'] if pd.notna(row['ocf_to_profit']) else None,
            cash_to_liqdebt=row['cash_to_liqdebt'] if pd.notna(row['cash_to_liqdebt']) else None,
            cash_to_liqdebt_withinterest=row['cash_to_liqdebt_withinterest'] if pd.notna(
                row['cash_to_liqdebt_withinterest']) else None,
            op_to_liqdebt=row['op_to_liqdebt'] if pd.notna(row['op_to_liqdebt']) else None,
            op_to_debt=row['op_to_debt'] if pd.notna(row['op_to_debt']) else None,
            roic_yearly=row['roic_yearly'] if pd.notna(row['roic_yearly']) else None,
            total_fa_trun=row['total_fa_trun'] if pd.notna(row['total_fa_trun']) else None,
            profit_to_op=row['profit_to_op'] if pd.notna(row['profit_to_op']) else None,
            q_opincome=row['q_opincome'] if pd.notna(row['q_opincome']) else None,
            q_investincome=row['q_investincome'] if pd.notna(row['q_investincome']) else None,
            q_dtprofit=row['q_dtprofit'] if pd.notna(row['q_dtprofit']) else None,
            q_eps=row['q_eps'] if pd.notna(row['q_eps']) else None,
            q_netprofit_margin=row['q_netprofit_margin'] if pd.notna(row['q_netprofit_margin']) else None,
            q_gsprofit_margin=row['q_gsprofit_margin'] if pd.notna(row['q_gsprofit_margin']) else None,
            q_exp_to_sales=row['q_exp_to_sales'] if pd.notna(row['q_exp_to_sales']) else None,
            q_profit_to_gr=row['q_profit_to_gr'] if pd.notna(row['q_profit_to_gr']) else None,
            q_saleexp_to_gr=row['q_saleexp_to_gr'] if pd.notna(row['q_saleexp_to_gr']) else None,
            q_adminexp_to_gr=row['q_adminexp_to_gr'] if pd.notna(row['q_adminexp_to_gr']) else None,
            q_finaexp_to_gr=row['q_finaexp_to_gr'] if pd.notna(row['q_finaexp_to_gr']) else None,
            q_impair_to_gr_ttm=row['q_impair_to_gr_ttm'] if pd.notna(row['q_impair_to_gr_ttm']) else None,
            q_gc_to_gr=row['q_gc_to_gr'] if pd.notna(row['q_gc_to_gr']) else None,
            q_op_to_gr=row['q_op_to_gr'] if pd.notna(row['q_op_to_gr']) else None,
            q_roe=row['q_roe'] if pd.notna(row['q_roe']) else None,
            q_dt_roe=row['q_dt_roe'] if pd.notna(row['q_dt_roe']) else None,
            q_npta=row['q_npta'] if pd.notna(row['q_npta']) else None,
            q_opincome_to_ebt=row['q_opincome_to_ebt'] if pd.notna(row['q_opincome_to_ebt']) else None,
            q_investincome_to_ebt=row['q_investincome_to_ebt'] if pd.notna(row['q_investincome_to_ebt']) else None,
            q_dtprofit_to_profit=row['q_dtprofit_to_profit'] if pd.notna(row['q_dtprofit_to_profit']) else None,
            q_salescash_to_or=row['q_salescash_to_or'] if pd.notna(row['q_salescash_to_or']) else None,
            q_ocf_to_sales=row['q_ocf_to_sales'] if pd.notna(row['q_ocf_to_sales']) else None,
            q_ocf_to_or=row['q_ocf_to_or'] if pd.notna(row['q_ocf_to_or']) else None,
            basic_eps_yoy=row['basic_eps_yoy'] if pd.notna(row['basic_eps_yoy']) else None,
            dt_eps_yoy=row['dt_eps_yoy'] if pd.notna(row['dt_eps_yoy']) else None,
            cfps_yoy=row['cfps_yoy'] if pd.notna(row['cfps_yoy']) else None,
            op_yoy=row['op_yoy'] if pd.notna(row['op_yoy']) else None,
            ebt_yoy=row['ebt_yoy'] if pd.notna(row['ebt_yoy']) else None,
            netprofit_yoy=row['netprofit_yoy'] if pd.notna(row['netprofit_yoy']) else None,
            dt_netprofit_yoy=row['dt_netprofit_yoy'] if pd.notna(row['dt_netprofit_yoy']) else None,
            ocf_yoy=row['ocf_yoy'] if pd.notna(row['ocf_yoy']) else None,
            roe_yoy=row['roe_yoy'] if pd.notna(row['roe_yoy']) else None,
            bps_yoy=row['bps_yoy'] if pd.notna(row['bps_yoy']) else None,
            assets_yoy=row['assets_yoy'] if pd.notna(row['assets_yoy']) else None,
            eqt_yoy=row['eqt_yoy'] if pd.notna(row['eqt_yoy']) else None,
            tr_yoy=row['tr_yoy'] if pd.notna(row['tr_yoy']) else None,
            or_yoy=row['or_yoy'] if pd.notna(row['or_yoy']) else None,
            q_gr_yoy=row['q_gr_yoy'] if pd.notna(row['q_gr_yoy']) else None,
            q_gr_qoq=row['q_gr_qoq'] if pd.notna(row['q_gr_qoq']) else None,
            q_sales_yoy=row['q_sales_yoy'] if pd.notna(row['q_sales_yoy']) else None,
            q_sales_qoq=row['q_sales_qoq'] if pd.notna(row['q_sales_qoq']) else None,
            q_op_yoy=row['q_op_yoy'] if pd.notna(row['q_op_yoy']) else None,
            q_op_qoq=row['q_op_qoq'] if pd.notna(row['q_op_qoq']) else None,
            q_profit_yoy=row['q_profit_yoy'] if pd.notna(row['q_profit_yoy']) else None,
            q_profit_qoq=row['q_profit_qoq'] if pd.notna(row['q_profit_qoq']) else None,
            q_netprofit_yoy=row['q_netprofit_yoy'] if pd.notna(row['q_netprofit_yoy']) else None,
            q_netprofit_qoq=row['q_netprofit_qoq'] if pd.notna(row['q_netprofit_qoq']) else None,
            equity_yoy=row['equity_yoy'] if pd.notna(row['equity_yoy']) else None,
            rd_exp=row['rd_exp'] if pd.notna(row['rd_exp']) else None,
            update_flag=row['update_flag'] if pd.notna(row['update_flag']) else None
        )
        batch_data.append(financial_data)
        total_count += 1

        # 当达到批量大小时，执行批量插入
        if len(batch_data) >= BATCH_SIZE:
            mapper.insert_financial_data_batch(batch_data)
            print(f"已处理 {total_count} 条数据，当前批次插入 {len(batch_data)} 条")
            batch_data = []  # 清空批量数据

    # 处理剩余的数据（不足100条的最后一批）
    if batch_data:
        mapper.insert_financial_data_batch(batch_data)
