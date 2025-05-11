from datetime import datetime, timedelta


def get_n_days_before(date_str, n):
    # 将输入的日期字符串转换为datetime对象
    date_format = "%Y%m%d"
    date_obj = datetime.strptime(date_str, date_format)

    # 计算N天前的日期
    n_days_before = date_obj - timedelta(days=n)

    # 将结果转换回字符串格式
    return n_days_before.strftime(date_format)