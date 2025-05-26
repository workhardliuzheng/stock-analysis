import matplotlib.pyplot as plt

from entity import constant

plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置默认 sans-serif 字体为 SimHei
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示问题

def plot_dual_y_axis_line_chart(data, x_column, y1_column, y2_column, y1_label, y2_label,
                                y1_scale_factor=1, y2_scale_factor=1, title="Dual Y-Axis Line Chart",
                                same_lim=False, is_save_picture=False):

    # Create the figure and the primary axis
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Plot the first y-axis data
    color1 = 'tab:red'
    ax1.set_xlabel(x_column)
    ax1.set_ylabel(y1_label, color=color1)
    ax1.plot(data[x_column], data[y1_column]/y1_scale_factor, color=color1, label=y1_label)
    ax1.tick_params(axis='y', labelcolor=color1)

    # Create a secondary y-axis that shares the same x-axis
    ax2 = ax1.twinx()
    color2 = 'tab:blue'
    ax2.set_ylabel(y2_label, color=color2)
    ax2.plot(data[x_column], data[y2_column]/y2_scale_factor, color=color2, label=y2_label)
    ax2.tick_params(axis='y', labelcolor=color2)

    if same_lim:
        xmin = min(min(data[x_column]), min(data[x_column]))
        xmax = max(max(data[x_column]), max(data[x_column]))
        ymin = min(min(data[y1_column]), min(data[y2_column]))
        ymax = max(max(data[y1_column]), max(data[y2_column]))

        ax1.set_xlim(xmin, xmax)
        ax1.set_ylim(ymin, ymax)

        ax2.set_xlim(xmin, xmax)
        ax2.set_ylim(ymin, ymax)


    # Set the title
    fig.suptitle(title)

    # Add legends
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc='upper left')

    # Show grid
    ax1.grid(True)

    # Display the plot
    if is_save_picture:
        plt.savefig(constant.DEFAULT_FILE_PATH + title + '.png', dpi=300, bbox_inches='tight')
    else:
        plt.show()