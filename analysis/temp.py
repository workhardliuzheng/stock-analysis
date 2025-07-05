import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import seaborn as sns


def plot_index_comprehensive_chart(df, ts_code, figsize=(16, 12), save_path=None):
    """
    绘制指数综合分析图表

    Args:
        df: 包含指数数据的DataFrame
        ts_code: 指数代码
        figsize: 图表大小
        save_path: 保存路径，如果为None则不保存
    """
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    # 创建子图
    fig, axes = plt.subplots(4, 2, figsize=figsize)
    fig.suptitle(f'{ts_code} 指数综合分析图表', fontsize=16, fontweight='bold')

    # 确保trade_date是datetime类型
    df['trade_date'] = pd.to_datetime(df['trade_date'])

    # 1. 指数价格走势
    ax1 = axes[0, 0]
    ax1.plot(df['trade_date'], df['close'], color='blue', linewidth=1.5)
    ax1.set_title('指数价格走势', fontsize=12, fontweight='bold')
    ax1.set_ylabel('收盘价')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=6))

    # 2. PE等权 vs PE加权
    ax2 = axes[0, 1]
    ax2.plot(df['trade_date'], df['pe'], color='red', linewidth=1.5, label='PE等权', alpha=0.8)
    ax2.plot(df['trade_date'], df['pe_weight'], color='darkred', linewidth=1.5, label='PE加权', alpha=0.8)
    ax2.set_title('PE估值对比', fontsize=12, fontweight='bold')
    ax2.set_ylabel('PE倍数')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=6))

    # 3. PE_TTM等权 vs PE_TTM加权
    ax3 = axes[1, 0]
    ax3.plot(df['trade_date'], df['pe_ttm'], color='green', linewidth=1.5, label='PE_TTM等权', alpha=0.8)
    ax3.plot(df['trade_date'], df['pe_ttm_weight'], color='darkgreen', linewidth=1.5, label='PE_TTM加权', alpha=0.8)
    ax3.set_title('PE_TTM估值对比', fontsize=12, fontweight='bold')
    ax3.set_ylabel('PE_TTM倍数')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=6))

    # 4. PB等权 vs PB加权
    ax4 = axes[1, 1]
    ax4.plot(df['trade_date'], df['pb'], color='orange', linewidth=1.5, label='PB等权', alpha=0.8)
    ax4.plot(df['trade_date'], df['pb_weight'], color='darkorange', linewidth=1.5, label='PB加权', alpha=0.8)
    ax4.set_title('PB估值对比', fontsize=12, fontweight='bold')
    ax4.set_ylabel('PB倍数')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax4.xaxis.set_major_locator(mdates.MonthLocator(interval=6))

    # 5. 估值分布直方图 - PE
    ax5 = axes[2, 0]
    pe_data = df['pe'].dropna()
    pe_weight_data = df['pe_weight'].dropna()
    ax5.hist(pe_data, bins=50, alpha=0.6, color='red', label='PE等权', density=True)
    ax5.hist(pe_weight_data, bins=50, alpha=0.6, color='darkred', label='PE加权', density=True)
    ax5.axvline(pe_data.iloc[-1], color='red', linestyle='--', label=f'当前PE等权: {pe_data.iloc[-1]:.2f}')
    ax5.axvline(pe_weight_data.iloc[-1], color='darkred', linestyle='--',
                label=f'当前PE加权: {pe_weight_data.iloc[-1]:.2f}')
    ax5.set_title('PE估值分布', fontsize=12, fontweight='bold')
    ax5.set_xlabel('PE倍数')
    ax5.set_ylabel('密度')
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # 6. 估值分布直方图 - PB
    ax6 = axes[2, 1]
    pb_data = df['pb'].dropna()
    pb_weight_data = df['pb_weight'].dropna()
    ax6.hist(pb_data, bins=50, alpha=0.6, color='orange', label='PB等权', density=True)
    ax6.hist(pb_weight_data, bins=50, alpha=0.6, color='darkorange', label='PB加权', density=True)
    ax6.axvline(pb_data.iloc[-1], color='orange', linestyle='--', label=f'当前PB等权: {pb_data.iloc[-1]:.2f}')
    ax6.axvline(pb_weight_data.iloc[-1], color='darkorange', linestyle='--',
                label=f'当前PB加权: {pb_weight_data.iloc[-1]:.2f}')
    ax6.set_title('PB估值分布', fontsize=12, fontweight='bold')
    ax6.set_xlabel('PB倍数')
    ax6.set_ylabel('密度')
    ax6.legend()
    ax6.grid(True, alpha=0.3)

    # 7. 价格与PE的关系散点图
    ax7 = axes[3, 0]
    scatter = ax7.scatter(df['pe'], df['close'], c=df.index, cmap='viridis', alpha=0.6, s=20)
    ax7.set_title('收盘价 vs PE等权关系', fontsize=12, fontweight='bold')
    ax7.set_xlabel('PE等权')
    ax7.set_ylabel('收盘价')
    ax7.grid(True, alpha=0.3)

    # 8. 估值百分位热力图（最近一年）
    ax8 = axes[3, 1]

    # 计算最近一年的百分位
    recent_data = df.tail(252)  # 最近一年
    metrics = ['pe', 'pb', 'pe_ttm']
    percentiles = []

    for metric in metrics:
        if metric in df.columns:
            valid_data = df[metric].dropna()
            if len(valid_data) > 0:
                current_value = recent_data[metric].iloc[-1]
                if pd.notna(current_value):
                    percentile = (valid_data < current_value).sum() / len(valid_data) * 100
                    percentiles.append(percentile)
                else:
                    percentiles.append(0)
            else:
                percentiles.append(0)
        else:
            percentiles.append(0)

    # 创建热力图数据
    heatmap_data = np.array(percentiles).reshape(1, -1)

    # 绘制热力图
    im = ax8.imshow(heatmap_data, cmap='RdYlGn_r', aspect='auto', vmin=0, vmax=100)
    ax8.set_xticks(range(len(metrics)))
    ax8.set_xticklabels([m.upper() for m in metrics])
    ax8.set_yticks([0])
    ax8.set_yticklabels(['当前百分位'])
    ax8.set_title('估值百分位热力图', fontsize=12, fontweight='bold')

    # 添加数值标签
    for i, percentile in enumerate(percentiles):
        ax8.text(i, 0, f'{percentile:.1f}%', ha='center', va='center',
                 color='white' if percentile > 50 else 'black', fontweight='bold')

    # 添加颜色条
    cbar = plt.colorbar(im, ax=ax8, shrink=0.8)
    cbar.set_label('百分位 (%)')

    # 调整布局
    plt.tight_layout()

    # 保存图表
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图表已保存到: {save_path}")

    plt.show()


def plot_percentile_trend(df, ts_code, figsize=(14, 10), save_path=None):
    """
    绘制百分位趋势图

    Args:
        df: 包含百分位数据的DataFrame
        ts_code: 指数代码
        figsize: 图表大小
        save_path: 保存路径
    """
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    fig, axes = plt.subplots(3, 1, figsize=figsize, sharex=True)
    fig.suptitle(f'{ts_code} 估值百分位趋势图', fontsize=16, fontweight='bold')

    # 确保trade_date是datetime类型
    df['trade_date'] = pd.to_datetime(df['trade_date'])

    metrics = [
        ('pe_percentile', 'PE百分位', 'red'),
        ('pb_percentile', 'PB百分位', 'orange'),
        ('pe_ttm_percentile', 'PE_TTM百分位', 'green')
    ]

    for i, (metric, title, color) in enumerate(metrics):
        ax = axes[i]

        if metric in df.columns:
            # 绘制百分位线
            ax.plot(df['trade_date'], df[metric], color=color, linewidth=2, label=title)

            # 添加百分位区间背景
            ax.axhspan(0, 10, alpha=0.2, color='green', label='极低估值区间(0-10%)')
            ax.axhspan(10, 25, alpha=0.15, color='lightgreen', label='低估值区间(10-25%)')
            ax.axhspan(75, 90, alpha=0.15, color='orange', label='高估值区间(75-90%)')
            ax.axhspan(90, 100, alpha=0.2, color='red', label='极高估值区间(90-100%)')

            # 添加参考线
            ax.axhline(y=50, color='gray', linestyle='--', alpha=0.7, label='中位数(50%)')
            ax.axhline(y=25, color='green', linestyle=':', alpha=0.7)
            ax.axhline(y=75, color='red', linestyle=':', alpha=0.7)

            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.set_ylabel('百分位 (%)')
            ax.set_ylim(0, 100)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper right', fontsize=8)

            # 显示当前值
            if not df[metric].empty:
                current_value = df[metric].iloc[-1]
                if pd.notna(current_value):
                    ax.text(0.02, 0.95, f'当前: {current_value:.1f}%',
                            transform=ax.transAxes, fontsize=10, fontweight='bold',
                            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # 设置x轴格式
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"百分位趋势图已保存到: {save_path}")

    plt.show()


# 使用示例
def example_plotting():
    """绘图使用示例"""
    # 假设你已经有了数据
    # analyzer = IndexAnalyzer(db_connection)
    # df = analyzer.get_index_data('000300.SH')

    # 绘制综合分析图表
    # plot_index_comprehensive_chart(df, '000300.SH', save_path='index_analysis.png')

    # 获取百分位趋势数据并绘图
    # trend_data = analyzer.analyze_percentile_trend('000300.SH', days=252)
    # plot_percentile_trend(trend_data, '000300.SH', save_path='percentile_trend.png')

    pass
