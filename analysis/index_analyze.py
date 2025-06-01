import pandas as pd

from entity import constant
from entity.stock_data import StockData
from mysql_connect.sixty_index_mapper import SixtyIndexMapper
from plot.plot_dual_y_axis_line_chart import plot_dual_y_axis_line_chart
import matplotlib.pyplot as plt

from util.class_util import ClassUtil
from util.date_util import TimeUtils

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

mapper = SixtyIndexMapper()


class StockAnalyzer:
    def __init__(self, ts_code):
        start_date = constant.HISTORY_START_DATE_MAP[ts_code]
        end_date = TimeUtils.get_current_date_str()

        index_data = mapper.select_by_code_and_trade_round(ts_code, start_date, end_date)

        data_frame_list = []
        for row in index_data:
            stock_data = ClassUtil.create_entities_from_data(StockData, row)
            data_frame_list.append(stock_data.to_dict())

        self.data = pd.DataFrame(data_frame_list)

    """分析偏离率分布"""
    def analyze_deviation_distribution(self):

        deviation_rates = self.data['deviation_rate'].dropna()

        # 统计分布
        stats = {
            '总样本数': len(deviation_rates),
            '平均偏离率': deviation_rates.mean(),
            '标准差': deviation_rates.std(),
            '最大偏离率': deviation_rates.max(),
            '最小偏离率': deviation_rates.min(),
            '中位数': deviation_rates.median()
        }

        # 分区间统计
        bins = [-float('inf'), -10, -5, -2, 0, 2, 5, 10, float('inf')]
        labels = ['<-10%', '-10%~-5%', '-5%~-2%', '-2%~0%', '0%~2%', '2%~5%', '5%~10%', '>10%']

        self.data['deviation_range'] = pd.cut(self.data['deviation_rate'], bins=bins, labels=labels)
        distribution = self.data['deviation_range'].value_counts().sort_index()

        print("=== 60日线偏离率分布统计 ===")
        for key, value in stats.items():
            if isinstance(value, float):
                print(f"{key}: {value:.4f}")
            else:
                print(f"{key}: {value}")

        print("\n=== 偏离率区间分布 ===")
        for range_name, count in distribution.items():
            percentage = count / len(deviation_rates) * 100
            print(f"{range_name}: {count}次 ({percentage:.2f}%)")

        return stats, distribution

    """分析不同偏离率下的未来走势"""
    def analyze_future_trend(self, future_days=[5, 10, 20]):

        results = {}
        for days in future_days:
            print(f"\n=== {days}日后走势分析 ===")

            # 计算未来收益率
            future_returns = []
            deviation_ranges = []

            for ts_code in self.data['ts_code'].unique():
                stock_data = self.data[self.data['ts_code'] == ts_code].copy()
                stock_data = stock_data.sort_values('trade_date').reset_index(drop=True)

                for i in range(len(stock_data) - days):
                    current_price = stock_data.iloc[i]['close']
                    future_price = stock_data.iloc[i + days]['close']
                    current_deviation = stock_data.iloc[i]['deviation_rate']

                    if pd.notna(current_deviation) and pd.notna(future_price):
                        future_return = (future_price - current_price) / current_price * 100
                        future_returns.append(future_return)
                        deviation_ranges.append(current_deviation)

            # 创建分析数据框
            analysis_df = pd.DataFrame({
                'deviation_rate': deviation_ranges,
                'future_return': future_returns
            })

            # 按偏离率分组分析
            bins = [-float('inf'), -10, -5, -2, 0, 2, 5, 10, float('inf')]
            labels = ['<-10%', '-10%~-5%', '-5%~-2%', '-2%~0%', '0%~2%', '2%~5%', '5%~10%', '>10%']

            analysis_df['deviation_range'] = pd.cut(analysis_df['deviation_rate'], bins=bins, labels=labels)

            # 统计各区间的未来收益
            range_analysis = analysis_df.groupby('deviation_range', observed=False)['future_return'].agg([
                'count', 'mean', 'std', 'min', 'max',
                lambda x: (x > 0).sum() / len(x) * 100  # 上涨概率
            ]).round(4)
            range_analysis.columns = ['样本数', '平均收益率%', '收益率标准差', '最小收益率%', '最大收益率%',
                                      '上涨概率%']

            print(range_analysis)
            results[f'{days}days'] = range_analysis

        return results

    """寻找反转点和稳定区间"""
    def find_reversal_points(self, extreme_threshold=5):
        print(f"\n=== 反转点分析（极值阈值: ±{extreme_threshold}%）===")

        reversal_analysis = []

        for ts_code in self.data['ts_code'].unique():
            stock_data = self.data[self.data['ts_code'] == ts_code].copy()
            stock_data = stock_data.sort_values('trade_date').reset_index(drop=True)

            # 寻找极值点
            for i in range(1, len(stock_data) - 20):  # 至少需要20天后续数据
                current_deviation = stock_data.iloc[i]['deviation_rate']

                if pd.isna(current_deviation):
                    continue

                # 判断是否为极值点
                if abs(current_deviation) >= extreme_threshold:
                    # 寻找后续稳定点
                    for j in range(i + 1, min(i + 61, len(stock_data))):  # 最多看60天
                        future_deviation = stock_data.iloc[j]['deviation_rate']

                        if pd.notna(future_deviation) and abs(future_deviation) <= 2:  # 稳定在±2%以内
                            days_to_stable = j - i
                            price_change = (stock_data.iloc[j]['close'] - stock_data.iloc[i]['close']) / \
                                           stock_data.iloc[i]['close'] * 100

                            reversal_analysis.append({
                                'start_date': stock_data.iloc[i]['trade_date'],
                                'start_deviation': current_deviation,
                                'stable_date': stock_data.iloc[j]['trade_date'],
                                'stable_deviation': future_deviation,
                                'days_to_stable': days_to_stable,
                                'price_change_pct': price_change,
                                'direction': 'up' if price_change > 0 else 'down'
                            })
                            break

        if reversal_analysis:
            reversal_df = pd.DataFrame(reversal_analysis)

            # 按起始偏离率分组统计
            positive_reversals = reversal_df[reversal_df['start_deviation'] > extreme_threshold]
            negative_reversals = reversal_df[reversal_df['start_deviation'] < -extreme_threshold]

            print(f"正偏离反转分析（偏离率>{extreme_threshold}%）:")
            if len(positive_reversals) > 0:
                print(f"  样本数: {len(positive_reversals)}")
                print(f"  平均稳定天数: {positive_reversals['days_to_stable'].mean():.1f}天")
                print(f"  平均价格变化: {positive_reversals['price_change_pct'].mean():.2f}%")
                print(
                    f"  下跌概率: {(positive_reversals['direction'] == 'down').sum() / len(positive_reversals) * 100:.1f}%")

            print(f"\n负偏离反转分析（偏离率<-{extreme_threshold}%）:")
            if len(negative_reversals) > 0:
                print(f"  样本数: {len(negative_reversals)}")
                print(f"  平均稳定天数: {negative_reversals['days_to_stable'].mean():.1f}天")
                print(f"  平均价格变化: {negative_reversals['price_change_pct'].mean():.2f}%")
                print(
                    f"  上涨概率: {(negative_reversals['direction'] == 'up').sum() / len(negative_reversals) * 100:.1f}%")

            return reversal_df
        else:
            print("未找到符合条件的反转点")
            return None

    """绘制分析图表"""
    def plot_analysis(self):

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('股票60日线偏离率分析', fontsize=16)

        # 1. 价格和60日均线走势
        sample_data = self.data[self.data['ts_code'] == self.data['ts_code'].iloc[0]].copy()
        sample_data = sample_data.sort_values('trade_date')

        axes[0, 0].plot(sample_data['trade_date'], sample_data['close'], label='收盘价', linewidth=1)
        axes[0, 0].plot(sample_data['trade_date'], sample_data['ma60'], label='60日均线', linewidth=2)
        axes[0, 0].set_title('价格走势与60日均线')
        axes[0, 0].legend()
        axes[0, 0].tick_params(axis='x', rotation=45)

        # 2. 偏离率时间序列
        axes[0, 1].plot(sample_data['trade_date'], sample_data['deviation_rate'], color='red', linewidth=1)
        axes[0, 1].axhline(y=0, color='black', linestyle='--', alpha=0.5)
        axes[0, 1].axhline(y=5, color='red', linestyle='--', alpha=0.5)
        axes[0, 1].axhline(y=-5, color='green', linestyle='--', alpha=0.5)
        axes[0, 1].set_title('60日线偏离率时间序列')
        axes[0, 1].set_ylabel('偏离率 (%)')
        axes[0, 1].tick_params(axis='x', rotation=45)

        # 3. 偏离率分布直方图
        deviation_rates = self.data['deviation_rate'].dropna()
        axes[1, 0].hist(deviation_rates, bins=50, alpha=0.7, color='skyblue', edgecolor='black')
        axes[1, 0].axvline(x=0, color='red', linestyle='--', alpha=0.7)
        axes[1, 0].set_title('偏离率分布直方图')
        axes[1, 0].set_xlabel('偏离率 (%)')
        axes[1, 0].set_ylabel('频次')

        # 4. 偏离率与未来收益散点图
        future_returns = []
        current_deviations = []

        for ts_code in self.data['ts_code'].unique():
            stock_data = self.data[self.data['ts_code'] == ts_code].copy()
            stock_data = stock_data.sort_values('trade_date').reset_index(drop=True)

            for i in range(len(stock_data) - 10):
                current_price = stock_data.iloc[i]['close']
                future_price = stock_data.iloc[i + 10]['close']
                current_deviation = stock_data.iloc[i]['deviation_rate']

                if pd.notna(current_deviation) and pd.notna(future_price):
                    future_return = (future_price - current_price) / current_price * 100
                    future_returns.append(future_return)
                    current_deviations.append(current_deviation)

        axes[1, 1].scatter(current_deviations, future_returns, alpha=0.5, s=10)
        axes[1, 1].axhline(y=0, color='red', linestyle='--', alpha=0.7)
        axes[1, 1].axvline(x=0, color='red', linestyle='--', alpha=0.7)
        axes[1, 1].set_title('当前偏离率 vs 10日后收益率')
        axes[1, 1].set_xlabel('当前偏离率 (%)')
        axes[1, 1].set_ylabel('10日后收益率 (%)')

        plt.tight_layout()
        plt.savefig('stock_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()


    # 收盘价与成交量的关系
    def plot_close_value_and_amount(self, ts_code):

        # 将字典列表转换为 DataFrame
        data_of_df = self.data
        name = constant.TS_CODE_NAME_DICT[ts_code]
        plot_dual_y_axis_line_chart(data_of_df, 'trade_date', 'close', 'amount', '收盘价', '成交量',
                                    y1_scale_factor=1, y2_scale_factor=100000,title=name + '收盘价与成交量图')

    # 收盘价与60日线关系
    def plot_close_value_and_sixty_average_amount(self, ts_code):
        # 将字典列表转换为 DataFrame
        data_of_df = self.data
        name = constant.TS_CODE_NAME_DICT[ts_code]
        plot_dual_y_axis_line_chart(data_of_df, 'trade_date', 'close', 'average_amount', '收盘价', '60日均线',
                                    y1_scale_factor=1, y2_scale_factor=1,title=name + '收盘价与60日均线图', same_lim=True)


    def all_analysis(self):
        """主函数"""
        print("=== 股票60日线偏离率分析系统 ===\n")

        # 分析偏离率分布
        stats, distribution = self.analyze_deviation_distribution()

        # 分析未来走势
        future_analysis = self.analyze_future_trend([5, 10, 20])

        # 寻找反转点
        reversal_points = self.find_reversal_points(extreme_threshold=5)

        # 绘制分析图表
        self.plot_analysis()

        print("\n=== 分析完成 ===")
        print("图表已保存为 stock_analysis.png")

        # 输出关键结论
        print("\n=== 关键结论 ===")
        deviation_rates = self.data['deviation_rate'].dropna()
        print(f"1. 偏离率主要分布在 ±{deviation_rates.std():.2f}% 范围内")
        print(
            f"2. 极端偏离率（>5%或<-5%）出现概率约为 {((abs(deviation_rates) > 5).sum() / len(deviation_rates) * 100):.1f}%")

        if reversal_points is not None and len(reversal_points) > 0:
            avg_days = reversal_points['days_to_stable'].mean()
            print(f"3. 极端偏离后平均 {avg_days:.1f} 天回归稳定区间")
