# 这是一个示例 Python 脚本。
import sync
from analysis.fund_analyze import FundAnalyze
from analysis.index_analyze import StockAnalyzer
from entity import constant
from sync import fund_data_sync as fds
from sync.index.sixty_index_analysis import SixtyIndexAnalysis
from sync.market_data import market_data_sync
from sync.market_data.market_data_sync import additional_data as sync_market_data
from sync.index.sync_stock_weight import additional_data as sync_stock_weight
from sync.index.sync_stock_weight import sync_stock_weight as sync_stock_weight_excect
from sync.stock.sync_income import additional_data as sync_income
from sync.stock.sync_financial_data import additional_data as sync_financial_data
import sync.stock.sync_financing_margin_trading



from sync.stock.sync_stock_basic import sync_all_stock_basic
from sync.stock.sync_stock_daily_basic import sync_all_stock_basic_daily
from util.date_util import TimeUtils

# 按 ⌃R 执行或将其替换为您的代码。
# 按 双击 ⇧ 在所有地方搜索类、文件、工具窗口、操作和设置。。


# 示例使用
if __name__ == "__main__":
    # 同步两融
    """print('同步两融')
    sync.stock.sync_financing_margin_trading.additional_data()
    analys = sync.index.sixty_index_analysis.SixtyIndexAnalysis()
    # 同步权重
    print('同步权重')
    print('同步各个公司财务合并数据')
    sync.index.sync_stock_weight.additional_data()
    # 同步etf市场数据
    #print('同步etf市场数据')
    #sync.market_data.market_data_sync.additional_data()
    # 同步收入数据
    print('同步收入数据')
    sync.stock.sync_income.additional_data()
    #同步各个公司财务合并数据
    print('同步各个公司财务合并数据')
    sync.stock.sync_financial_data.additional_data()
    #同步各个公司基础书籍
    print('同步各个公司基础数据')
    sync.stock.sync_stock_basic.sync_all_stock_basic()
    #同步各个公司股票数据
    print('同步各个公司股票数据')
    sync.stock.sync_stock_daily_basic.sync_all_stock_basic_daily()
    # 同步指数书籍
    print('同步指数数据')
    sixty_analysis = SixtyIndexAnalysis()
    sixty_analysis.additional_data('20200101')

    for ts_code in constant.TS_CODE_LIST:
        ana = StockAnalyzer(ts_code, '20200101')"""

    ana = StockAnalyzer('399001.SZ', '20200101')
    ana.plot_percentiles('pe')