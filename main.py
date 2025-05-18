# 这是一个示例 Python 脚本。
import mysql_connect
from mysql_connect.database_manager import DatabaseManager
from stock_index_analysis.sixty_index_analysis import SixtyIndexAnalysis


# 按 ⌃R 执行或将其替换为您的代码。
# 按 双击 ⇧ 在所有地方搜索类、文件、工具窗口、操作和设置。。


# 示例使用
if __name__ == "__main__":
    stock = SixtyIndexAnalysis()
    stock.additional_data()
    #stock.init_sixty_index_average_value('399001.SZ', '20150512', '20150513')
    print("同步结束")