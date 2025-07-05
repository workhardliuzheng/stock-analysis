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
        # 处理日期字段，将空字符串转换为None
        list_date = row['list_date'] if pd.notna(row['list_date']) and row['list_date'] != '' else None
        delist_date = row['delist_date'] if pd.notna(row['delist_date']) and row['delist_date'] != '' else None

        # 创建股票基础信息对象
        stock_basic = StockBasic(
            id=None,
            ts_code=row['ts_code'],
            symbol=row['symbol'],
            name=row['name'],
            area=row['area'] if pd.notna(row['area']) else None,
            industry=row['industry'] if pd.notna(row['industry']) else None,
            fullname=row['fullname'] if pd.notna(row['fullname']) else None,
            enname=row['enname'] if pd.notna(row['enname']) else None,
            cnspell=row['cnspell'] if pd.notna(row['cnspell']) else None,
            market=row['market'] if pd.notna(row['market']) else None,
            exchange=row['exchange'] if pd.notna(row['exchange']) else None,
            curr_type=row['curr_type'] if pd.notna(row['curr_type']) else None,
            list_status=row['list_status'] if pd.notna(row['list_status']) else None,
            list_date=list_date,
            delist_date=delist_date,
            is_hs=row['is_hs'] if pd.notna(row['is_hs']) else None
        )

        batch_data.append(stock_basic)
        total_count += 1

        # 当达到批量大小时，执行批量插入或更新
        if len(batch_data) >= BATCH_SIZE:
            _process_batch_data(batch_data)
            print(f"已处理 {total_count} 条数据，当前批次处理 {len(batch_data)} 条")
            batch_data = []

    # 处理剩余的数据
    if batch_data:
        _process_batch_data(batch_data)
        print(f"最后批次处理 {len(batch_data)} 条数据")

    print(f"股票基础信息处理完成，共处理 {total_count} 条数据")

def _process_batch_data(batch_data):
    """处理批量数据，支持插入和更新"""
    try:
        # 先尝试批量插入，如果存在重复则进行更新
        for stock_basic in batch_data:
            existing_stock = mapper.get_stock_basic_by_ts_code(stock_basic.get_ts_code())
            if existing_stock:
                # 更新现有记录
                stock_basic.set_id(existing_stock.id)
                mapper.update_stock_basic(stock_basic)
            else:
                # 插入新记录
                mapper.insert_stock_basic(stock_basic)

    except Exception as e:
        print(f"批量处理数据失败: {e}")
        # 如果批量处理失败，尝试逐条处理
        for stock_basic in batch_data:
            try:
                existing_stock = mapper.get_stock_basic_by_ts_code(stock_basic.get_ts_code())
                if existing_stock:
                    stock_basic.set_id(existing_stock.id)
                    mapper.update_stock_basic(stock_basic)
                else:
                    mapper.insert_stock_basic(stock_basic)
            except Exception as single_error:
                print(f"处理股票 {stock_basic.get_ts_code()} 失败: {single_error}")

def update_stock_basic():
    """增量更新股票基础信息"""
    try:
        # 获取最近更新的股票信息（通常股票基础信息变化不频繁，可以定期全量更新）
        sync_all_stock_basic()
    except Exception as e:
        print(f"更新股票基础信息失败: {e}")
