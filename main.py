# 这是一个示例 Python 脚本。
import mysql_connect
from mysql_connect.database_manager import DatabaseManager


# 按 ⌃R 执行或将其替换为您的代码。
# 按 双击 ⇧ 在所有地方搜索类、文件、工具窗口、操作和设置。


def print_hi(name):
    # 在下面的代码行中使用断点来调试脚本。
    print(f'Hi, {name}')  # 按 ⌘F8 切换断点。


# 示例使用
if __name__ == "__main__":
    db_manager = DatabaseManager()  # 不需要传入配置文件路径
    db_manager.connect()

    # 插入数据
    data_to_insert = {
        'id': 1,
        'average_day': 5,
        'ts_code': '000001.SH',
        'average_value': 100.5,
        'index_value': 102.3,
        'trade_date': '2023-10-01',
        'deviation_rate': 1.8
    }
    db_manager.insert('daliy_moving_average', data_to_insert)

    # 查询数据
    result = db_manager.select('daliy_moving_average', condition="id = 1")
    print("查询结果:", result)

    # 更新数据
    data_to_update = {
        'average_value': 101.5,
        'index_value': 103.3
    }
    db_manager.update('daliy_moving_average', data_to_update, condition="id = 1")

    # 再次查询数据
    result = db_manager.select('daliy_moving_average', condition="id = 1")
    print("更新后的查询结果:", result)

    # 删除数据
    db_manager.delete('daliy_moving_average', condition="id = 1")

    # 最后查询数据
    result = db_manager.select('daliy_moving_average', condition="id = 1")
    print("删除后的查询结果:", result)

    db_manager.disconnect()