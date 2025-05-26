from entity import constant
from entity.stock_data import StockData
from mysql_connect.sixty_index_mapper import SixtyIndexMapper
from plot.plot_dual_y_axis_line_chart import plot_dual_y_axis_line_chart
import pandas as pd

from util.class_util import ClassUtil


# 收盘价与成交量的关系
def plot_close_value_and_amount(ts_code):
    mapper = SixtyIndexMapper()
    data= mapper.select_by_code(ts_code)

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