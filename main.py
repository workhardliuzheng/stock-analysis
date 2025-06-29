# 这是一个示例 Python 脚本。
from analysis.fund_analyze import FundAnalyze
from analysis.index_analyze import StockAnalyzer
from entity import constant
from sync import fund_data_sync as fds
from sync.index.sixty_index_analysis import SixtyIndexAnalysis
from sync.market_data import market_data_sync
from sync.market_data.market_data_sync import additional_data
from sync.index.sync_stock_weight import additional_data as sync_stock_weight

# 按 ⌃R 执行或将其替换为您的代码。
# 按 双击 ⇧ 在所有地方搜索类、文件、工具窗口、操作和设置。。


# 示例使用
if __name__ == "__main__":
    sync_stock_weight()

    #six = SixtyIndexAnalysis()
    #res = six.get_index_pe_pb('000300.SH', '20250101', '20250228')

    #print(res)
    #market_data_sync.additional_data()
    #analysis = StockAnalyzer('399001.SZ')
    #analysis.all_analysis()
    #fund_map = constant.FUND_NAME_MAP
    #for ts_code in fund_map.keys():
    #    fund_data_sync.cal_average(ts_code)
    #fund_analyze = FundAnalyze('159920.SZ')
    #fund_analyze.plot_close_and_deviation_from_m60()
    #fds.additional_data()

