import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from entity import constant
from entity.fund_data import FundData
from mysql_connect.fund_data_mapper import FundDataMapper
from mysql_connect.fund_mapper import FundMapper
from util.class_util import ClassUtil
from util.date_util import TimeUtils

FUND_DATA_FIELDS = [
    "ts_code",
    "trade_date",
    "pre_close",
    "open",
    "high",
    "low",
    "close",
    "change",
    "pct_chg",
    "vol",
    "amount"
]
LIMIT = 1000
fund_data_mapper = FundDataMapper()
fund_mapper = FundMapper()

class FundAnalyze:
    def __init__(self, ts_code):
        found_date = fund_mapper.get_found_date(ts_code)
        min_date = fund_data_mapper.get_min_trade_time(ts_code)

        if min_date:
            start_date = TimeUtils.date_to_str(found_date)
            end_date = TimeUtils.get_current_date_str()
        else:
            start_date = TimeUtils.date_to_str(found_date)
            end_date = TimeUtils.get_current_date_str()

        fund_data = fund_data_mapper.select_by_code_and_trade_round(ts_code, start_date, end_date)

        data_frame_list = []
        for row in fund_data:
            stock_data = ClassUtil.create_entities_from_data(FundData, row)
            data_frame_list.append(stock_data.to_dict())

        self.data = pd.DataFrame(data_frame_list)
        self.ts_code=ts_code

    def analyze(self):
        data = self.data
        # 计算收盘价与20日线的偏离度（百分比）
        data['deviation_from_m20_pct'] = ((data['close'] - data['m20']) / data['m20']) * 100

        # 计算RSI
        def calculate_rsi(data, window=14):
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi

        data['rsi'] = calculate_rsi(data)

        # 寻找买入和卖出点
        buy_signals = []
        sell_signals = []

        for i in range(1, len(data)):
            if data['m5'].iloc[i] > data['m20'].iloc[i] and data['m5'].iloc[i - 1] <= data['m20'].iloc[i - 1]:
                if data['rsi'].iloc[i] < 30:  # RSI低于30表示超卖
                    buy_signals.append((data['trade_date'].iloc[i], data['close'].iloc[i]))
            elif data['m5'].iloc[i] < data['m20'].iloc[i] and data['m5'].iloc[i - 1] >= data['m20'].iloc[i - 1]:
                if data['rsi'].iloc[i] > 70:  # RSI高于70表示超买
                    sell_signals.append((data['trade_date'].iloc[i], data['close'].iloc[i]))

        print("Buy Signals:", buy_signals)
        print("Sell Signals:", sell_signals)

        # 绘制收盘价、各均线及其偏离度
        plt.figure(figsize=(14, 7))

        plt.plot(data['trade_date'], data['close'], label='Close Price', color='blue')
        plt.plot(data['trade_date'], data['m5'], label='5 Day MA', color='orange', linestyle='--')
        plt.plot(data['trade_date'], data['m10'], label='10 Day MA', color='green', linestyle='-.')
        plt.plot(data['trade_date'], data['m20'], label='20 Day MA', color='red', linestyle='-')
        plt.plot(data['trade_date'], data['m60'], label='60 Day MA', color='purple', linestyle=':')
        plt.plot(data['trade_date'], data['m120'], label='120 Day MA', color='black', linestyle='-.')
        plt.fill_between(data['trade_date'], data['close'], data['m20'], where=data['close'] > data['m20'],
                         color='lightcoral', alpha=0.3)
        plt.fill_between(data['trade_date'], data['close'], data['m20'], where=data['close'] < data['m20'],
                         color='lightgreen', alpha=0.3)

        # 标记买入和卖出点
        for date, price in buy_signals:
            plt.scatter(date, price, marker='^', color='green', s=100, label='Buy Signal' if not any(
                label.get_text() == 'Buy Signal' for label in plt.gca().get_legend_handles_labels()[1]) else "")
        for date, price in sell_signals:
            plt.scatter(date, price, marker='v', color='red', s=100, label='Sell Signal' if not any(
                label.get_text() == 'Sell Signal' for label in plt.gca().get_legend_handles_labels()[1]) else "")
        name = constant.FUND_NAME_MAP[self.ts_code]
        plt.title(f'{name} Close Price and Moving Averages with Deviation from 20 Day MA (%)')
        plt.xlabel('Trade Date')
        plt.ylabel('Price (yuan)')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()

        # 显示图形
        plt.show()

        # 统计持有时间和价格与20日线偏离度的关系
        holdings = []
        current_hold = None
