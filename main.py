"""
股票分析系统 - 统一入口

支持两种运行模式：
1. sync - 数据同步（同步指数、股票、财务等数据）
2. plot - 图表生成（生成技术分析图表）

使用示例：
    python main.py sync                      # 同步所有数据
    python main.py sync --index-only         # 仅同步指数数据
    python main.py plot                      # 生成所有图表
    python main.py plot --ts-code 000001.SH  # 生成指定指数图表
    python main.py plot --show               # 生成并显示图表
"""
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='股票分析系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py sync                      同步所有数据
  python main.py sync --index-only         仅同步指数数据
  python main.py plot                      生成所有图表
  python main.py plot --ts-code 000001.SH  生成指定指数图表
  python main.py plot --show               生成并显示图表
        """
    )
    parser.add_argument('mode', choices=['sync', 'plot'], help='运行模式: sync(数据同步) 或 plot(图表生成)')
    parser.add_argument('--start-date', default='20200101', help='同步开始日期 (默认: 20200101)')
    parser.add_argument('--index-only', action='store_true', help='仅同步指数数据 (sync模式)')
    parser.add_argument('--ts-code', help='指定指数代码 (plot模式)')
    parser.add_argument('--save-dir', help='图表保存目录 (plot模式)')
    parser.add_argument('--show', action='store_true', help='显示图表 (plot模式)')
    args = parser.parse_args()
    
    if args.mode == 'sync':
        from sync_main import sync_all, sync_index_only
        if args.index_only:
            sync_index_only(args.start_date)
        else:
            sync_all(args.start_date)
    
    elif args.mode == 'plot':
        from plot_main import plot_all, plot_single
        if args.ts_code:
            plot_single(args.ts_code, save_dir=args.save_dir, show=args.show)
        else:
            plot_all(save_dir=args.save_dir, show=args.show)