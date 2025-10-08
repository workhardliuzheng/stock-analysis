import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from entity import constant
from entity.stock_data import StockData
from mysql_connect.sixty_index_mapper import SixtyIndexMapper
from plot.plot_dual_y_axis_line_chart import plot_dual_y_axis_line_chart, DataPltMetadata

from util.class_util import ClassUtil
from util.date_util import TimeUtils


# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

mapper = SixtyIndexMapper()


class StockAnalyzer:
    def __init__(self, ts_code, start_date):
        end_date = TimeUtils.get_current_date_str()

        index_data = mapper.select_by_code_and_trade_round(ts_code, start_date, end_date)

        data_frame_list = []
        for row in index_data:
            stock_data = ClassUtil.create_entities_from_data(StockData, row)
            data_frame_list.append(stock_data.to_dict())

        self.data = pd.DataFrame(data_frame_list)
        self.name = constant.TS_CODE_NAME_DICT[ts_code]
        self.ts_code = ts_code

    def plot_all_zhishu(self, is_save_picture):
        columns = None
        if self.ts_code == '399001.SZ':
            columns = ['pe_ttm_weight', 'pe_weight', 'pb_weight', 'pe_profit_dedt', 'pe_profit_dedt_ttm', 'pe_ttm',
                   'pe', 'pb']
        elif self.ts_code == '399006.SZ':
            columns = ['pe_ttm_weight', 'pb']
        elif self.ts_code == '000001.SH':
            columns = ['pe']
        elif self.ts_code == '000300.SH':
            columns = ['pe_ttm_weight', 'pe_weight', 'pb_weight', 'pe_profit_dedt', 'pe_profit_dedt_ttm', 'pe_ttm',
                   'pe', 'pb']
        elif self.ts_code == '000688.SH':
            columns = ['pb']
        elif self.ts_code == '000852.SH':
            columns = ['pb_weight']
        elif self.ts_code == '000905.SH':
            columns = ['pb_weight']
        elif self.ts_code == '000016.SH':
            columns = ['pb_weight']
        if columns is None:
            return

        print(f"=================={self.name}数据 =====================")
        for column in columns:
            self._plot(column, column, is_save_picture, '财务加权')

        # 偏移率
        self._plot('deviation_rate', 'deviation_rate', True, '60日线偏移度')

        #成交量
        self._plot('amount', 'amount', True, '成交量')
        print()


    def _plot(self, column, label, is_save_picture, dir_name):
        data = self.data
        left_data = DataPltMetadata('close', '收盘价', 1, 'red', linestyle='-')
        right_data = DataPltMetadata(column, label, 1, 'blue', linestyle='-')
        left_plot_metadata_list = [left_data]
        right_plot_metadata_list = [right_data]

        # 直接获取 trade_date 最大的那行的 pe 值
        max_pe_value = data.loc[data['trade_date'].idxmax(), column]
        percent = self._calculate_percentile(column, max_pe_value)
        print(f"{self.name}的{column}处于整体的: {percent}")


        file_path = constant.DEFAULT_FILE_PATH + dir_name +'\\'
        name = f"{self.name}与{column}"
        plot_dual_y_axis_line_chart(data, x_column='trade_date', left_plot_metadata_list=left_plot_metadata_list,
                                    right_plot_metadata_list=right_plot_metadata_list, is_save_picture=is_save_picture,
                                    title=name, file_path=file_path)

    def _calculate_percentile(self, column_name, value):
        data = self.data.copy()
        """
        计算某个值在DataFrame指定列中的百分位

        参数:
        df: pandas DataFrame
        column_name: str, 列名
        value: 要计算百分位的值

        返回:
        float: 百分位值(0-100之间)
        """

        # 获取列数据并移除NaN值
        data['Rank'] = data[column_name].rank(method='min')

        # 计算总行数
        total_rows = len(data)

        # 计算百分位数
        return (data[data[column_name] == value]['Rank'].iloc[0] - 1) / (total_rows - 1) * 100

    def plot_percentiles(self, column_name):
        data = self.data

        data.sort_values(by=column_name, inplace=True)
        percentile_30_index = int(len(data) * 0.2)

        top_30_percentile = data.head(percentile_30_index)
        bottom_70_percentile = data.tail(int(len(data) * 0.2))

        # Reset index to align with original dataframe
        top_30_percentile.reset_index(drop=True, inplace=True)
        bottom_70_percentile.reset_index(drop=True, inplace=True)

        # Plot all data points
        plt.figure(figsize=(14, 7))
        plt.plot(data['trade_date'], data[column_name], label='All Data', color='blue', alpha=0.5)

        # Highlight top 30%
        plt.scatter(top_30_percentile['trade_date'], top_30_percentile[column_name], label='Top 30%', color='red', s=50,
                    zorder=5)

        # Highlight bottom 70%
        plt.scatter(bottom_70_percentile['trade_date'], bottom_70_percentile[column_name], label='Bottom 70%',
                    color='red', s=50, zorder=5)

        plt.title(column_name)
        plt.xlabel('Trade Date')
        plt.ylabel(column_name)
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
