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
        # 生成数据
        income_data = Income(
            id=None,
            ts_code=row['ts_code'] if pd.notna(row['ts_code']) else None,
            ann_date=row['ann_date'] if pd.notna(row['ann_date']) else None,
            f_ann_date=row['f_ann_date'] if pd.notna(row['f_ann_date']) else None,
            end_date=row['end_date'] if pd.notna(row['end_date']) else None,
            report_type=row['report_type'] if pd.notna(row['report_type']) else None,
            comp_type=row['comp_type'] if pd.notna(row['comp_type']) else None,
            end_type=row['end_type'] if pd.notna(row['end_type']) else None,
            basic_eps=row['basic_eps'] if pd.notna(row['basic_eps']) else None,
            diluted_eps=row['diluted_eps'] if pd.notna(row['diluted_eps']) else None,
            total_revenue=row['total_revenue'] if pd.notna(row['total_revenue']) else None,
            revenue=row['revenue'] if pd.notna(row['revenue']) else None,
            int_income=row['int_income'] if pd.notna(row['int_income']) else None,
            prem_earned=row['prem_earned'] if pd.notna(row['prem_earned']) else None,
            comm_income=row['comm_income'] if pd.notna(row['comm_income']) else None,
            n_commis_income=row['n_commis_income'] if pd.notna(row['n_commis_income']) else None,
            n_oth_income=row['n_oth_income'] if pd.notna(row['n_oth_income']) else None,
            n_oth_b_income=row['n_oth_b_income'] if pd.notna(row['n_oth_b_income']) else None,
            prem_income=row['prem_income'] if pd.notna(row['prem_income']) else None,
            out_prem=row['out_prem'] if pd.notna(row['out_prem']) else None,
            une_prem_reser=row['une_prem_reser'] if pd.notna(row['une_prem_reser']) else None,
            reins_income=row['reins_income'] if pd.notna(row['reins_income']) else None,
            n_sec_tb_income=row['n_sec_tb_income'] if pd.notna(row['n_sec_tb_income']) else None,
            n_sec_uw_income=row['n_sec_uw_income'] if pd.notna(row['n_sec_uw_income']) else None,
            n_asset_mg_income=row['n_asset_mg_income'] if pd.notna(row['n_asset_mg_income']) else None,
            oth_b_income=row['oth_b_income'] if pd.notna(row['oth_b_income']) else None,
            fv_value_chg_gain=row['fv_value_chg_gain'] if pd.notna(row['fv_value_chg_gain']) else None,
            invest_income=row['invest_income'] if pd.notna(row['invest_income']) else None,
            ass_invest_income=row['ass_invest_income'] if pd.notna(row['ass_invest_income']) else None,
            forex_gain=row['forex_gain'] if pd.notna(row['forex_gain']) else None,
            total_cogs=row['total_cogs'] if pd.notna(row['total_cogs']) else None,
            oper_cost=row['oper_cost'] if pd.notna(row['oper_cost']) else None,
            int_exp=row['int_exp'] if pd.notna(row['int_exp']) else None,
            comm_exp=row['comm_exp'] if pd.notna(row['comm_exp']) else None,
            biz_tax_surchg=row['biz_tax_surchg'] if pd.notna(row['biz_tax_surchg']) else None,
            sell_exp=row['sell_exp'] if pd.notna(row['sell_exp']) else None,
            admin_exp=row['admin_exp'] if pd.notna(row['admin_exp']) else None,
            fin_exp=row['fin_exp'] if pd.notna(row['fin_exp']) else None,
            assets_impair_loss=row['assets_impair_loss'] if pd.notna(row['assets_impair_loss']) else None,
            prem_refund=row['prem_refund'] if pd.notna(row['prem_refund']) else None,
            compens_payout=row['compens_payout'] if pd.notna(row['compens_payout']) else None,
            reser_insur_liab=row['reser_insur_liab'] if pd.notna(row['reser_insur_liab']) else None,
            div_payt=row['div_payt'] if pd.notna(row['div_payt']) else None,
            reins_exp=row['reins_exp'] if pd.notna(row['reins_exp']) else None,
            oper_exp=row['oper_exp'] if pd.notna(row['oper_exp']) else None,
            compens_payout_refu=row['compens_payout_refu'] if pd.notna(row['compens_payout_refu']) else None,
            insur_reser_refu=row['insur_reser_refu'] if pd.notna(row['insur_reser_refu']) else None,
            reins_cost_refund=row['reins_cost_refund'] if pd.notna(row['reins_cost_refund']) else None,
            other_bus_cost=row['other_bus_cost'] if pd.notna(row['other_bus_cost']) else None,
            operate_profit=row['operate_profit'] if pd.notna(row['operate_profit']) else None,
            non_oper_income=row['non_oper_income'] if pd.notna(row['non_oper_income']) else None,
            non_oper_exp=row['non_oper_exp'] if pd.notna(row['non_oper_exp']) else None,
            nca_disploss=row['nca_disploss'] if pd.notna(row['nca_disploss']) else None,
            total_profit=row['total_profit'] if pd.notna(row['total_profit']) else None,
            income_tax=row['income_tax'] if pd.notna(row['income_tax']) else None,
            n_income=row['n_income'] if pd.notna(row['n_income']) else None,
            n_income_attr_p=row['n_income_attr_p'] if pd.notna(row['n_income_attr_p']) else None,
            minority_gain=row['minority_gain'] if pd.notna(row['minority_gain']) else None,
            oth_compr_income=row['oth_compr_income'] if pd.notna(row['oth_compr_income']) else None,
            t_compr_income=row['t_compr_income'] if pd.notna(row['t_compr_income']) else None,
            compr_inc_attr_p=row['compr_inc_attr_p'] if pd.notna(row['compr_inc_attr_p']) else None,
            compr_inc_attr_m_s=row['compr_inc_attr_m_s'] if pd.notna(row['compr_inc_attr_m_s']) else None,
            ebit=row['ebit'] if pd.notna(row['ebit']) else None,
            ebitda=row['ebitda'] if pd.notna(row['ebitda']) else None,
            insurance_exp=row['insurance_exp'] if pd.notna(row['insurance_exp']) else None,
            undist_profit=row['undist_profit'] if pd.notna(row['undist_profit']) else None,
            distable_profit=row['distable_profit'] if pd.notna(row['distable_profit']) else None,
            rd_exp=row['rd_exp'] if pd.notna(row['rd_exp']) else None,
            fin_exp_int_exp=row['fin_exp_int_exp'] if pd.notna(row['fin_exp_int_exp']) else None,
            fin_exp_int_inc=row['fin_exp_int_inc'] if pd.notna(row['fin_exp_int_inc']) else None,
            transfer_surplus_rese=row['transfer_surplus_rese'] if pd.notna(row['transfer_surplus_rese']) else None,
            transfer_housing_imprest=row['transfer_housing_imprest'] if pd.notna(
                row['transfer_housing_imprest']) else None,
            transfer_oth=row['transfer_oth'] if pd.notna(row['transfer_oth']) else None,
            adj_lossgain=row['adj_lossgain'] if pd.notna(row['adj_lossgain']) else None,
            withdra_legal_surplus=row['withdra_legal_surplus'] if pd.notna(row['withdra_legal_surplus']) else None,
            withdra_legal_pubfund=row['withdra_legal_pubfund'] if pd.notna(row['withdra_legal_pubfund']) else None,
            withdra_biz_devfund=row['withdra_biz_devfund'] if pd.notna(row['withdra_biz_devfund']) else None,
            withdra_rese_fund=row['withdra_rese_fund'] if pd.notna(row['withdra_rese_fund']) else None,
            withdra_oth_ersu=row['withdra_oth_ersu'] if pd.notna(row['withdra_oth_ersu']) else None,
            workers_welfare=row['workers_welfare'] if pd.notna(row['workers_welfare']) else None,
            distr_profit_shrhder=row['distr_profit_shrhder'] if pd.notna(row['distr_profit_shrhder']) else None,
            prfshare_payable_dvd=row['prfshare_payable_dvd'] if pd.notna(row['prfshare_payable_dvd']) else None,
            comshare_payable_dvd=row['comshare_payable_dvd'] if pd.notna(row['comshare_payable_dvd']) else None,
            capit_comstock_div=row['capit_comstock_div'] if pd.notna(row['capit_comstock_div']) else None,
            net_after_nr_lp_correct=row['net_after_nr_lp_correct'] if pd.notna(
                row['net_after_nr_lp_correct']) else None,
            oth_income=row['oth_income'] if pd.notna(row['oth_income']) else None,
            asset_disp_income=row['asset_disp_income'] if pd.notna(row['asset_disp_income']) else None,
            continued_net_profit=row['continued_net_profit'] if pd.notna(row['continued_net_profit']) else None,
            end_net_profit=row['end_net_profit'] if pd.notna(row['end_net_profit']) else None,
            credit_impa_loss=row['credit_impa_loss'] if pd.notna(row['credit_impa_loss']) else None,
            net_expo_hedging_benefits=row['net_expo_hedging_benefits'] if pd.notna(
                row['net_expo_hedging_benefits']) else None,
            oth_impair_loss_assets=row['oth_impair_loss_assets'] if pd.notna(row['oth_impair_loss_assets']) else None,
            total_opcost=row['total_opcost'] if pd.notna(row['total_opcost']) else None,
            amodcost_fin_assets=row['amodcost_fin_assets'] if pd.notna(row['amodcost_fin_assets']) else None,
            update_flag=row['update_flag'] if pd.notna(row['update_flag']) else None
        )
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
