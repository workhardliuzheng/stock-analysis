import numpy as np
import pandas as pd

from entity import constant
from entity.stock_data import StockData
from mysql_connect.sixty_index_mapper import SixtyIndexMapper
from plot.plot_dual_y_axis_line_chart import plot_dual_y_axis_line_chart
from util.class_util import ClassUtil
import matplotlib.pyplot as plt

mapper = SixtyIndexMapper()
def analyze_deviation_distribution(ts_code):
    data = mapper.select_by_code_and_trade_round(ts_code, constant.HISTORY_START_DATE_MAP[ts_code],
                                          mapper.get_max_trade_time(ts_code))
    data_dicts = []
    for list in data:
        one_date = ClassUtil.create_entities_from_data(StockData, list)
        data_dicts.append(one_date.to_dict())

    # 将字典列表转换为 DataFrame
    df = pd.DataFrame(data_dicts)

    mean = df['deviation_rate'].mean()
    std = df['deviation_rate'].std()
    percentiles = np.percentile(df['deviation_rate'], [5, 25, 50, 75, 95])
    print(f"均值: {mean:.4f}, 标准差: {std:.4f}")
    print(f"分位数: 5%={percentiles[0]:.4f}, 25%={percentiles[1]:.4f}, "
          f"50%={percentiles[2]:.4f}, 75%={percentiles[3]:.4f}, 95%={percentiles[4]:.4f}")

    # 可视化
    import matplotlib.pyplot as plt
    df['deviation_rate'].hist(bins=50, alpha=0.7)
    plt.title("Deviation Rate Distribution")
    plt.xlabel("Deviation Rate")
    plt.ylabel("Frequency")
    plt.show()

def analyze_deviation_future_return(ts_code, future_days=5, bins=10):
    """
    分析指定指数代码的历史偏移率与未来 n 个交易日涨幅之间的关系。

    参数:
        ts_code (str): 指数代码，如 '000001.SH'
        future_days (int): 要预测的未来交易日天数
        bins (int): 偏移率分箱数量
    """
    # 获取历史数据
    start_date = constant.HISTORY_START_DATE_MAP.get(ts_code)
    end_date = mapper.get_max_trade_time(ts_code)

    if not start_date or not end_date:
        print("缺少起始或结束日期")
        return

    data = mapper.select_by_code_and_trade_round(ts_code, start_date, end_date)

    if not data:
        print(f"未查询到 {ts_code} 的相关数据")
        return

    # 转换为 DataFrame
    data_dicts = [ClassUtil.create_entities_from_data(StockData, row).to_dict() for row in data]
    df = pd.DataFrame(data_dicts)
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df.sort_values('trade_date', inplace=True)

    # 计算未来收盘价和收益率
    df['future_close'] = df['close'].shift(-future_days)
    df['future_return'] = (df['future_close'] - df['close']) / df['close']

    # 删除 NaN 值（最后 few rows）
    df.dropna(subset=['future_close', 'future_return'], inplace=True)

    # 对偏移率进行分箱
    df['deviation_bin'] = pd.qcut(df['deviation_rate'], q=bins)

    # 分组统计平均未来收益
    grouped = df.groupby('deviation_bin')['future_return'].mean().reset_index()
    grouped['future_days'] = future_days
    grouped['bin_center'] = grouped['deviation_bin'].apply(lambda x: x.mid)

    print("\n偏移率区间 vs 平均未来涨幅（{}个交易日后）:".format(future_days))
    print(grouped[['deviation_bin', 'bin_center', 'future_return']].round(4))

    # 可视化
    plt.figure(figsize=(12, 6))
    plt.bar(grouped['bin_center'], grouped['future_return'], width=grouped['deviation_bin'].apply(lambda x: x.length),
            color='skyblue', edgecolor='black', alpha=0.7)
    plt.axhline(0, color='red', linestyle='--', linewidth=1)
    plt.title(f"{ts_code} 偏移率区间 vs 未来 {future_days} 个交易日平均涨幅", fontsize=14)
    plt.xlabel("偏移率区间中位数", fontsize=12)
    plt.ylabel("平均涨幅", fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.show()

    return grouped

# 收盘价与成交量的关系
def plot_close_value_and_amount(ts_code, start_date, end_date):
    mapper = SixtyIndexMapper()
    data= mapper.select_by_code_and_trade_round(ts_code)

    data_dicts = []
    for list in data:
        one_date = ClassUtil.create_entities_from_data(StockData, list)
        data_dicts.append(one_date.to_dict())

    # 将字典列表转换为 DataFrame
    data_of_df = pd.DataFrame(data_dicts)
    name = constant.TS_CODE_NAME_DICT[ts_code]
    plot_dual_y_axis_line_chart(data_of_df, 'trade_date', 'close', 'amount', '收盘价', '成交量',
                                y1_scale_factor=1, y2_scale_factor=100000,title=name + '收盘价与成交量图')

# 收盘价与60日线关系
def plot_close_value_and_sixty_average_amount(ts_code, start_date, end_date):
    mapper = SixtyIndexMapper()
    data= mapper.select_by_code_and_trade_round(ts_code, start_date, end_date)

    data_dicts = []
    for list in data:
        one_date = ClassUtil.create_entities_from_data(StockData, list)
        data_dicts.append(one_date.to_dict())

    # 将字典列表转换为 DataFrame
    data_of_df = pd.DataFrame(data_dicts)
    name = constant.TS_CODE_NAME_DICT[ts_code]
    plot_dual_y_axis_line_chart(data_of_df, 'trade_date', 'close', 'average_amount', '收盘价', '60日均线',
                                y1_scale_factor=1, y2_scale_factor=1,title=name + '收盘价与60日均线图', same_lim=True)