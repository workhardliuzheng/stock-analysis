from datetime import datetime, timedelta
import pandas as pd

from entity.stock_basic import StockBasic
from mysql_connect.stock_basic_mapper import StockBasicMapper
from tu_share_factory.tu_share_factory import TuShareFactory

mapper = StockBasicMapper()
def sync_all_stock_basic():
    """同步所有股票基础信息"""
    try:
        # 获取所有上市状态的股票
        sync_stock_basic_by_status('L')  # 上市
        sync_stock_basic_by_status('D')  # 退市
        sync_stock_basic_by_status('P')  # 暂停上市
        print("股票基础信息同步完成")
    except Exception as e:
        print(f"同步股票基础信息失败: {e}")

def sync_stock_basic_by_status(list_status='L'):
    """
    根据上市状态同步股票基础信息
    :param list_status: L上市 D退市 P暂停上市
    """
    pro = TuShareFactory.build_api_client()

    try:
        # 获取股票基础信息
        print(f"开始获取上市状态为 {list_status} 的股票基础信息...")
        stock_basic_df = pro.stock_basic(exchange='',
                                       list_status=list_status,
                                       fields='ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs')

        if stock_basic_df.empty:
            print(f"未获取到上市状态为 {list_status} 的股票数据")
            return

        print(f"获取到 {len(stock_basic_df)} 条股票基础信息")

        # 批量处理数据
        batch_process_stock_basic(stock_basic_df)

    except Exception as e:
        print(f"获取股票基础信息失败: {e}")
        raise

def batch_process_stock_basic(stock_basic_df):
    """批量处理股票基础信息"""
    BATCH_SIZE = 100
    batch_data = []
    total_count = 0

    for _, row in stock_basic_df.iterrows():
        # 使用 from_df_row 自动转换，无需手动处理每个字段
        stock_basic = StockBasic.from_df_row(row)

        batch_data.append(stock_basic)
        total_count += 1

        # 当达到批量大小时，执行批量插入或更新
        if len(batch_data) >= BATCH_SIZE:
            mapper.upsert_stock_basic_batch(batch_data)
            print(f"已处理 {total_count} 条数据，当前批次处理 {len(batch_data)} 条")
            batch_data = []

    # 处理剩余的数据
    if batch_data:
        mapper.upsert_stock_basic_batch(batch_data)
        print(f"最后批次处理 {len(batch_data)} 条数据")

    print(f"股票基础信息处理完成，共处理 {total_count} 条数据")