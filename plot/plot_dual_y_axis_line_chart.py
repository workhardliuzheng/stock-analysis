import matplotlib.pyplot as plt

from entity import constant

plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置默认 sans-serif 字体为 SimHei
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示问题

class DataPltMetadata():
    def __init__(self, column, label, scale_factor, color, linestyle):
        self.column = column
        self.label = label
        self.scale_factor = 1 if scale_factor is None else scale_factor
        self.color = color
        self.linestyle = linestyle

def plot_dual_y_axis_line_chart(data, x_column, left_plot_metadata_list, right_plot_metadata_list,
                                title="Dual Y-Axis Line Chart",
                                same_lim=False, is_save_picture=False):

    # Create the figure and the primary axis
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax_list = []
    # Plot the first y-axis data
    ax1.set_xlabel(x_column)
    for metadata in left_plot_metadata_list:
        ax1.plot(data[x_column], data[metadata.column] / metadata.scale_factor,
                 label=metadata.label, color=metadata.color, linestyle=metadata.linestyle)

    if right_plot_metadata_list:
        ax2 = ax1.twinx()
        for metadata in right_plot_metadata_list:
            ax2.plot(data[x_column], data[metadata.column] / metadata.scale_factor,
                     label=metadata.label, color=metadata.color, linestyle=metadata.linestyle)

    if same_lim:
        xmin = min(min(data[x_column]), min(data[x_column]))
        xmax = max(max(data[x_column]), max(data[x_column]))

        ymin = min(data[left_plot_metadata_list[0].column])
        ymax = max(data[left_plot_metadata_list[0].column])

        if right_plot_metadata_list:
            ymin = min(ymin, min(data[right_plot_metadata_list[0].column]))
            ymax = max(ymax, max(data[right_plot_metadata_list[0].column]))

        ax1.set_xlim(xmin, xmax)
        ax1.set_ylim(ymin, ymax)

        if right_plot_metadata_list:
            ax2.set_xlim(xmin, xmax)
            ax2.set_ylim(ymin, ymax)


    # Set the title
    fig.suptitle(title)

    # Show grid
    ax1.grid(True)

    # Display the plot
    if is_save_picture:
        plt.savefig(constant.DEFAULT_FILE_PATH + title + '.png', dpi=300, bbox_inches='tight')
    else:
        plt.show()