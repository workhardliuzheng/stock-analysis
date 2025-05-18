from datetime import datetime, timedelta
DATE_FORMAT = "%Y%m%d"

class TimeUtils:
    @staticmethod
    def get_current_date_str() -> str:
        return datetime.now().strftime("%Y%m%d")

    @staticmethod
    def date_to_str(dt) -> str:

        return dt.strftime(DATE_FORMAT)

    @staticmethod
    def str_to_date(date_string) -> datetime:
        return datetime.strptime(date_string, DATE_FORMAT)

    @staticmethod
    def get_n_days_before_or_after(date_str, n, is_before=True) -> str:
        # 将输入的日期字符串转换为datetime对象
        date_obj = datetime.strptime(date_str, DATE_FORMAT)

        # 计算N天前的日期
        if is_before:
            n_days_before = date_obj - timedelta(days=n)
        else:
            n_days_before = date_obj + timedelta(days=n)

        # 将结果转换回字符串格式
        return n_days_before.strftime(DATE_FORMAT)

    @staticmethod
    def compare_date_str(date_str1: str, date_str2: str) -> int:
        d1 = datetime.strptime(date_str1, DATE_FORMAT)
        d2 = datetime.strptime(date_str2, DATE_FORMAT)

        if d1 > d2:
            return 1
        elif d1 < d2:
            return -1
        else:
            return 0
    @staticmethod
    def add_days_to_date_str(date_str: str, days: int) -> str:
        # 将字符串转换为datetime对象
        date_obj = datetime.strptime(date_str, DATE_FORMAT)
        # 加上指定天数
        new_date = date_obj + timedelta(days=days)
        # 返回格式化后的字符串
        return new_date.strftime(DATE_FORMAT)