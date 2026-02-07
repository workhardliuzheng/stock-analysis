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
        # 使用 from_df_row 自动转换，无需手动处理每个字段
        financial_data = FinancialData.from_df_row(row)
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
