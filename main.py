"""
股票分析系统 - 统一入口 (整合版)

支持六种运行模式：
1. sync         - 数据同步（同步指数、股票、财务等数据）
2. plot         - 图表生成（生成技术分析图表）
3. signal       - 信号生成（生成指数ETF买卖信号）
4. backtest     - 策略回测（回测多因子/ML/混合策略）
5. daily_report - 全天流程（同步+分析+报表+推送）
6. guide        - 使用指南（显示每日操作流程）

使用示例：
    python main.py sync                              # 同步所有数据
    python main.py sync --index-only                 # 仅同步指数数据
    python main.py plot                              # 生成所有图表
    python main.py plot --ts-code 000001.SH          # 生成指定指数图表
    python main.py signal                            # 生成所有指数今日信号
    python main.py signal --ts-code 000300.SH        # 生成沪深300今日信号
    python main.py backtest                          # 回测所有指数所有策略
    python main.py backtest --ts-code 000300.SH      # 回测沪深300
    python main.py daily_report                      # 全天流程：同步+分析+报表+邮件推送
    python main.py daily_report --to-email user@example.com  # 指定收件人
    python main.py guide                             # 显示每日操作流程
"""
import argparse
import os
from datetime import datetime


def print_guide():
    """打印每日操作指南"""
    print("""
================================================================================
                        股票分析系统 - 每日操作指南
================================================================================

一、每日操作流程
----------------

  1. 运行时间: 每个交易日 15:30 之后（等待收盘数据就绪）

  2. 数据同步:
     > python main.py sync --index-only

  3. 信号生成 (使用集成模型):
     > python main.py signal
     > python main.py signal --model-type ensemble     # 等价，默认集成模型
     > python main.py signal --model-type xgboost      # 仅用 XGBoost

  4. 查看信号后操作:
     - BUY  信号 -> 次日(T+1)开盘时 买入 对应指数ETF
     - SELL 信号 -> 次日(T+1)开盘时 卖出 持有的ETF
     - HOLD 信号 -> 不操作，维持当前仓位

二、一键全天流程（推荐）
----------------

  自动完成：数据同步 → 信号分析 → 报表生成 → 邮件推送
  > python main.py daily_report
  
  指定收件人：
  > python main.py daily_report --to-email user@example.com
  > python main.py daily_report --to-email user1@example.com,user2@example.com

三、回测验证
------------

  基本回测 (含手续费，收盘价执行):
  > python main.py backtest

  更贴近实盘的回测 (T+1开盘价执行):
  > python main.py backtest --execution-timing open

  自定义佣金率 (例如股票万0.85):
  > python main.py backtest --commission 0.000085

  单指数回测:
  > python main.py backtest --ts-code 000300.SH --execution-timing open

四、执行时机说明
----------------

  本系统使用 T日收盘数据 生成信号，信号在 T+1日 执行：

  (1) T+1 开盘价执行 (--execution-timing open) [推荐]
      - 更贴近实际操作：看到信号后次日开盘买入/卖出
      - 适合集合竞价或开盘后短时间内操作
      - 回测结果更保守、更真实

  (2) T+1 收盘价执行 (--execution-timing close) [默认]
      - 假设在次日收盘前完成操作
      - 回测结果可能略偏乐观

五、手续费说明
--------------

  默认佣金: 万0.6 (ETF交易佣金)
  - 买入和卖出各收取一次
  - 可通过 --commission 参数调整
  - 例如: 股票万0.85 = 0.000085

六、ML模型说明
--------------

  系统支持三种模型:
  - ensemble  (默认) : XGBoost + LightGBM 集成，取概率平均，效果最稳定
  - xgboost          : 仅使用 XGBoost
  - lightgbm         : 仅使用 LightGBM（更快）

  ML模型预测的是次日收益率大小（回归模型），并转换为交易信号。
  信号阈值: 预测收益 > 0.1% → BUY, < -0.1% → SELL, 中间 → HOLD
  可选 --auto-tune 启用 Optuna 超参数自动调优（耗时较长）

七、注意事项
------------

  - 该系统用于辅助投资决策，不构成投资建议
  - 回测结果不代表未来收益
  - 建议结合基本面分析和市场环境综合判断
  - 首次运行需要先同步历史数据: python main.py sync

================================================================================
""")


def run_daily_workflow(to_emails=None):
    """
    运行每日全流程：数据同步 -> 信号分析 -> 报表生成 -> 邮件推送

    使用 report/ 包的统一模块完成报告生成和邮件发送。
    """
    import subprocess
    import sys

    print("=" * 60)
    print("[START] 开始每日工作流")
    print("=" * 60)

    # 1. 数据同步
    print("\n[STEP 1] 同步指数数据...")
    print("-" * 40)
    try:
        result = subprocess.run(
            [sys.executable, __file__, 'sync', '--index-only'],
            capture_output=True,
            text=True,
            timeout=900
        )
        if result.returncode == 0:
            print("[OK] 数据同步成功")
        else:
            print(f"[WARNING] 数据同步警告: {result.stderr}")
    except Exception as e:
        print(f"[ERROR] 数据同步失败: {str(e)}")
        return

    # 2. 信号分析 - 收集所有指数的当日信号数据
    print("\n[STEP 2] 分析数据生成信号...")
    print("-" * 40)
    signals_data = []
    try:
        from analysis.index_analyzer import IndexAnalyzer
        from entity import constant

        codes = list(constant.TS_CODE_NAME_DICT.keys())
        for i, code in enumerate(codes):
            name = constant.TS_CODE_NAME_DICT.get(code, code)
            print(f"  [{i+1}/{len(codes)}] {name} ({code})...", end=" ", flush=True)
            try:
                analyzer = IndexAnalyzer(code)
                analyzer.analyze(include_ml=True)
                sig = analyzer.get_current_signal()
                if sig:
                    signals_data.append(sig)
                    print(f"OK -> {sig.get('final_signal', 'N/A')}")
                else:
                    print("无信号数据")
            except Exception as e:
                print(f"失败: {e}")

        print(f"\n[OK] 信号分析完成，共 {len(signals_data)} 个指数")
    except Exception as e:
        print(f"[ERROR] 信号分析失败: {str(e)}")
        return

    if not signals_data:
        print("[ERROR] 无信号数据可生成报告")
        return

    # 3. 生成报告
    print("\n[STEP 3] 生成投资报告...")
    print("-" * 40)
    report_result = None
    try:
        from report.report_generator import UnifiedReportGenerator
        gen = UnifiedReportGenerator()
        report_result = gen.generate(signals_data)

        # 打印文本报告到控制台
        print(report_result.text)
    except Exception as e:
        print(f"[ERROR] 报告生成失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # 4. 发送邮件
    if report_result:
        to_emails_display = to_emails if to_emails else "默认收件人"
        print(f"\n[STEP 4] 发送邮件至 {to_emails_display}...")
        print("-" * 40)

        try:
            from report.email_sender import EmailSender
            sender = EmailSender()

            to_list = [e.strip() for e in to_emails.split(',')] if to_emails else None

            subject = datetime.now().strftime('%Y-%m-%d') + " 市场分析报告"
            success, msg = sender.send(
                subject=subject,
                html_content=report_result.html,
                to_emails=to_list,
                attachment_path=report_result.html_path,
            )

            if not success:
                print(f"[WARNING] 邮件发送未成功: {msg}")
            else:
                print(f"[OK] 邮件发送成功")
        except Exception as e:
            print(f"[ERROR] 邮件发送失败: {str(e)}")
    else:
        print("\n[SKIP] 报告生成未完成，跳过邮件发送")

    print("\n" + "=" * 60)
    print("[DONE] 每日工作流完成!")
    print("=" * 60)


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
  python main.py signal --model-type ensemble      使用集成模型
  python main.py signal --auto-tune                启用Optuna超参数调优
  python main.py backtest                          回测所有指数所有策略
  python main.py backtest --ts-code 000300.SH      回测沪深300
  python main.py backtest --start-date 20230401 --end-date 20241001  回测特定时段
  python main.py backtest --strategy factor        仅回测多因子策略
  python main.py backtest --execution-timing open  T+1开盘价执行(更真实)
  python main.py backtest --commission 0.000085    自定义佣金率
  python main.py daily_report                      全天流程：同步+分析+报表
  python main.py daily_report --to-email user@example.com  邮件推送
  python main.py guide                            显示每日操作指南
        """
    )
    parser.add_argument('mode', 
                        choices=['sync', 'plot', 'signal', 'backtest', 'daily_report', 'guide'],
                        help='运行模式: sync/plot/signal/backtest/daily_report/guide')
    parser.add_argument('--start-date', default='20200101', help='同步/回测开始日期 (默认: 20200101)')
    parser.add_argument('--end-date', default=None, help='回测结束日期 (默认: 当前日期, 格式: YYYYMMDD)')
    parser.add_argument('--index-only', action='store_true', help='仅同步指数数据 (sync模式)')
    parser.add_argument('--ts-code', help='指定指数代码')
    parser.add_argument('--save-dir', help='图表保存目录 (plot模式)')
    parser.add_argument('--show', action='store_true', help='显示图表 (plot模式)')
    parser.add_argument('--to-emails', help='收件人邮箱 (daily_report模式，逗号分隔)')
    parser.add_argument('--strategy', default='all',
                        choices=['factor', 'ml', 'combined', 'all'],
                        help='回测策略: factor/ml/combined/all (默认: all)')
    parser.add_argument('--no-ml', action='store_true', help='不使用ML预测 (signal/backtest模式)')
    parser.add_argument('--model-type', default='ensemble',
                        choices=['xgboost', 'lightgbm', 'ensemble'],
                        help='ML模型类型 (默认: ensemble)')
    parser.add_argument('--execution-timing', default='close',
                        choices=['open', 'close'],
                        help='回测执行时机: open(T+1开盘价)/close(T+1收盘价) (默认: close)')
    parser.add_argument('--commission', type=float, default=0.00006,
                        help='单边佣金率 (默认: 0.00006 即万0.6)')
    parser.add_argument('--auto-tune', action='store_true',
                        help='启用 Optuna 超参数自动调优 (signal/backtest模式，耗时较长)')
    parser.add_argument('--feature-selection', action='store_true',
                        help='启用特征重要性筛选 (signal/backtest模式)')
    parser.add_argument('--smart-position', action='store_true',
                        help='启用V9智能仓位管理 (backtest模式)')
    parser.add_argument('--no-cross-consensus', action='store_true',
                        help='禁用V12跨指数趋势共识 (backtest模式)')
    parser.add_argument('--no-macro', action='store_true',
                        help='禁用V13宏观因子 (signal/backtest模式)')
    parser.add_argument('--no-bond', action='store_true',
                        help='禁用V17债券跷跷板 (backtest模式，默认启用国债ETF 511010.SH)')
    args = parser.parse_args()
    
    # 日期校验
    if args.end_date:
        if len(args.end_date) != 8 or not args.end_date.isdigit():
            parser.error(f"--end-date 格式错误: {args.end_date}，应为 YYYYMMDD (8位数字)")
        if args.start_date > args.end_date:
            parser.error(f"--end-date ({args.end_date}) 不能早于 --start-date ({args.start_date})")
    
    if args.mode == 'guide':
        print_guide()
    
    elif args.mode == 'sync':
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
            include_ml=not args.no_ml,
            auto_tune=args.auto_tune,
            include_macro=not args.no_macro,
            model_type=args.model_type,
            feature_selection=args.feature_selection
        )
    
    elif args.mode == 'daily_report':
        run_daily_workflow(args.to_emails)
    
    elif args.mode == 'backtest':
        from analysis.index_analyzer import portfolio_backtest
        portfolio_backtest(
            start_date=args.start_date,
            end_date=args.end_date,
            commission_rate=args.commission,
            use_smart_position=args.smart_position,
            cross_index_consensus=not args.no_cross_consensus,
            include_macro=not args.no_macro,
            # 排除上证综指（作为市场观察指数，不持仓）+ 红利低波(已用国债ETF替代)
            exclude_codes={'000001.SH', '930955.CSI'},
            # 沪深300限仓10%（避免重仓低效贡献）
            index_max_weight={'000300.SH': 0.10},
            # V17: 债券跷跷板，默认启用国债ETF
            bond_etf_code=None if args.no_bond else '511010.SH',
        )
