"""
股票分析系统 - 统一入口

支持四种运行模式：
1. sync     - 数据同步（同步指数、股票、财务等数据）
2. plot     - 图表生成（生成技术分析图表）
3. signal   - 信号生成（生成指数ETF买卖信号）
4. backtest - 策略回测（回测多因子/ML/混合策略）

使用示例：
    python main.py sync                              # 同步所有数据
    python main.py sync --index-only                 # 仅同步指数数据
    python main.py plot                              # 生成所有图表
    python main.py plot --ts-code 000001.SH          # 生成指定指数图表
    python main.py signal                            # 生成所有指数今日信号
    python main.py signal --ts-code 000300.SH        # 生成沪深300今日信号
    python main.py backtest                          # 回测所有指数所有策略
    python main.py backtest --ts-code 000300.SH      # 回测沪深300
    python main.py backtest --strategy factor         # 仅回测多因子策略
"""
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='股票分析系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py sync                              同步所有数据
  python main.py sync --index-only                 仅同步指数数据
  python main.py plot                              生成所有图表
  python main.py plot --ts-code 000001.SH          生成指定指数图表
  python main.py plot --show                       生成并显示图表
  python main.py signal                            生成所有指数今日信号
  python main.py signal --ts-code 000300.SH        生成沪深300今日信号
  python main.py signal --no-ml                    不使用ML预测
  python main.py backtest                          回测所有指数所有策略
  python main.py backtest --ts-code 000300.SH      回测沪深300
  python main.py backtest --strategy factor        仅回测多因子策略
  python main.py backtest --strategy ml            仅回测ML策略
  python main.py backtest --strategy combined      仅回测混合策略
        """
    )
    parser.add_argument('mode', choices=['sync', 'plot', 'signal', 'backtest'],
                        help='运行模式: sync(数据同步) / plot(图表生成) / signal(信号生成) / backtest(策略回测)')
    parser.add_argument('--start-date', default='20200101', help='同步/回测开始日期 (默认: 20200101)')
    parser.add_argument('--index-only', action='store_true', help='仅同步指数数据 (sync模式)')
    parser.add_argument('--ts-code', help='指定指数代码')
    parser.add_argument('--save-dir', help='图表保存目录 (plot模式)')
    parser.add_argument('--show', action='store_true', help='显示图表 (plot模式)')
    parser.add_argument('--strategy', default='all',
                        choices=['factor', 'ml', 'combined', 'all'],
                        help='回测策略: factor/ml/combined/all (默认: all)')
    parser.add_argument('--no-ml', action='store_true', help='不使用ML预测 (signal/backtest模式)')
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
    
    elif args.mode == 'signal':
        from analysis.index_analyzer import signal_all_indices
        signal_all_indices(
            ts_code=args.ts_code,
            include_ml=not args.no_ml
        )
    
    elif args.mode == 'backtest':
        from analysis.index_analyzer import backtest_all_indices
        backtest_all_indices(
            ts_code=args.ts_code,
            strategy=args.strategy,
            include_ml=not args.no_ml
        )
