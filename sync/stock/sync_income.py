# 自动同步数据
import time
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from entity import constant
from entity.income import Income
from mysql_connect.income_mapper import IncomeMapper
from mysql_connect.stock_basic_mapper import StockBasicMapper
from sync.index.sixty_index_analysis import stock_basic_mapper
from tu_share_factory.tu_share_factory import TuShareFactory
from util.date_util import TimeUtils

mapper = IncomeMapper()
stock_basic_mapper = StockBasicMapper()
INCOME_FIELDS = ["ts_code", "ann_date", "f_ann_date", "end_date", "report_type", "comp_type", "end_type", "basic_eps",
                 "diluted_eps", "total_revenue", "revenue", "int_income", "prem_earned", "comm_income",
                 "n_commis_income",
                 "n_oth_income", "n_oth_b_income", "prem_income", "out_prem", "une_prem_reser", "reins_income",
                 "n_sec_tb_income", "n_sec_uw_income", "n_asset_mg_income", "oth_b_income", "fv_value_chg_gain",
                 "invest_income", "ass_invest_income", "forex_gain", "total_cogs", "oper_cost", "int_exp", "comm_exp",
                 "biz_tax_surchg", "sell_exp", "admin_exp", "fin_exp", "assets_impair_loss", "prem_refund",
                 "compens_payout",
                 "reser_insur_liab", "div_payt", "reins_exp", "oper_exp", "compens_payout_refu", "insur_reser_refu",
                 "reins_cost_refund",
                 "other_bus_cost", "operate_profit", "non_oper_income", "non_oper_exp", "nca_disploss", "total_profit",
                 "income_tax", "n_income", "n_income_attr_p", "minority_gain", "oth_compr_income", "t_compr_income",
                 "compr_inc_attr_p", "compr_inc_attr_m_s", "ebit", "ebitda", "insurance_exp", "undist_profit",
                 "distable_profit",
                 "rd_exp", "fin_exp_int_exp", "fin_exp_int_inc", "transfer_surplus_rese", "transfer_housing_imprest",
                 "transfer_oth", "adj_lossgain", "withdra_legal_surplus", "withdra_legal_pubfund",
                 "withdra_biz_devfund",
                 "withdra_rese_fund", "withdra_oth_ersu", "workers_welfare", "distr_profit_shrhder",
                 "prfshare_payable_dvd",
                 "comshare_payable_dvd", "capit_comstock_div", "continued_net_profit", "update_flag",
                 "net_after_nr_lp_correct",
                 "oth_income", "asset_disp_income", "end_net_profit", "credit_impa_loss", "net_expo_hedging_benefits",
                 "oth_impair_loss_assets", "total_opcost", "amodcost_fin_assets"]


def additional_data():
    ts_code_list = stock_basic_mapper.get_all_ts_codes()

    for ts_code in ts_code_list:
        start_date = mapper.get_max_end_date(ts_code=ts_code)
        start_date = start_date if start_date else '19000101'
        time.sleep(0.3)
        try:
            sync_income_data(ts_code, start_date, TimeUtils.get_current_date_str())
        except Exception as e:
            print(f'插入股票{ts_code} 收入数据失败: {e}')
            time.sleep(30)
            sync_income_data(ts_code, start_date, TimeUtils.get_current_date_str())


def sync_income_data(ts_code:str, start_date:str, end_date:str):
    pro = TuShareFactory.build_api_client()

    # 批量大小
    BATCH_SIZE = 100

    # 获取当前月份的财务数据
    income_info = pro.income(ts_code=ts_code, start_date=start_date,
                             end_date=end_date, fields=INCOME_FIELDS)
    if income_info.empty:
        return

    # 去重并存储
    month_income_info = income_info.drop_duplicates(subset='end_date', keep='first')

    # 准备批量数据
    batch_data = []
    total_count = 0

    for _, row in month_income_info.iterrows():
        # 使用 from_df_row 自动转换，无需手动处理每个字段
        income_data = Income.from_df_row(row)
        batch_data.append(income_data)
        total_count += 1

        # 当达到批量大小时，执行批量插入
        if len(batch_data) >= BATCH_SIZE:
            mapper.insert_income_batch(batch_data)
            print(f"已处理 {total_count} 条数据，当前批次插入 {len(batch_data)} 条")
            batch_data = []  # 清空批量数据

    # 处理剩余的数据（不足100条的最后一批）
    if batch_data:
        mapper.insert_income_batch(batch_data)
        print(f"最后批次插入 {len(batch_data)} 条数据")

    print(f"股票 {ts_code} 处理完成，共处理 {total_count} 条数据")
