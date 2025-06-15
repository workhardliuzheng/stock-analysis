# 这是一个示例 Python 脚本。
from analysis.index_analyze import StockAnalyzer
from entity import constant
from sync import fund_data_sync
from sync.index.sixty_index_analysis import SixtyIndexAnalysis
from sync.market_data import market_data_sync
from sync.market_data.market_data_sync import additional_data

# 按 ⌃R 执行或将其替换为您的代码。
# 按 双击 ⇧ 在所有地方搜索类、文件、工具窗口、操作和设置。。


# 示例使用
if __name__ == "__main__":
    #six = SixtyIndexAnalysis()
    #six.additional_data()

    #market_data_sync.additional_data()
    #analysis = StockAnalyzer('399001.SZ')
    #analysis.all_analysis()
    fund_map = constant.FUND_NAME_MAP
    for ts_code in fund_map.keys():
        fund_data_sync.cal_average(ts_code)

