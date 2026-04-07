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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header


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


def send_email(subject, html_content, to_emails, smtp_config=None):
    """
    发送邮件
    
    Args:
        subject: 邮件主题
        html_content: HTML格式的邮件内容
        to_emails: 收件人邮箱列表（字符串或列表）
        smtp_config: SMTP配置，格式：
            {
                'host': 'smtp.example.com',
                'port': 587,
                'user': 'user@example.com',
                'password': 'app_password',
                'from_email': 'user@example.com'
            }
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    # 如果没有配置，尝试从环境变量读取
    if smtp_config is None:
        smtp_config = {
            'host': os.environ.get('SMTP_HOST', 'smtp.gmail.com'),
            'port': int(os.environ.get('SMTP_PORT', '587')),
            'user': os.environ.get('SMTP_USER', ''),
            'password': os.environ.get('SMTP_PASSWORD', ''),
            'from_email': os.environ.get('SMTP_FROM', os.environ.get('SMTP_USER', ''))
        }
    
    # 收件人处理
    if isinstance(to_emails, str):
        to_emails = [email.strip() for email in to_emails.split(',')]
    
    # 创建邮件
    msg = MIMEMultipart('related')
    msg['From'] = Header(smtp_config['from_email'], 'utf-8')
    msg['To'] = Header(','.join(to_emails), 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    
    # 添加HTML内容
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    
    # 如果有附件
    report_file = r'E:\pycharm\stock-analysis\daily_report.html'
    if os.path.exists(report_file):
        with open(report_file, 'rb') as f:
            att = MIMEText(f.read(), 'base64', 'utf-8')
            att['Content-Type'] = 'application/octet-stream'
            att['Content-Disposition'] = 'attachment; filename="daily_report.html"'
            msg.attach(att)
    
    # 发送邮件
    try:
        server = smtplib.SMTP(smtp_config['host'], smtp_config['port'])
        server.starttls()
        server.login(smtp_config['user'], smtp_config['password'])
        server.sendmail(smtp_config['from_email'], to_emails, msg.as_string())
        server.quit()
        return True, "邮件发送成功"
    except Exception as e:
        return False, f"邮件发送失败: {str(e)}"


def generate_html_report(signals_data, indices_info=None):
    """
    生成HTML格式的日报
    
    Args:
        signals_data: 信号数据字典，格式：{ts_code: {'signal': 'BUY/SELL/HOLD', 'confidence': 0.8, ...}}
        indices_info: 指数信息映射
    
    Returns:
        html_content: HTML格式的报告内容
    """
    if indices_info is None:
        indices_info = {
            '000688.SH': '科创50',
            '399006.SZ': '创业板指',
            '000001.SH': '上证综指',
            '000905.SH': '中证500',
            '000852.SH': '中证1000',
            '000300.SH': '沪深300',
            '399001.SZ': '深证成指',
            '000016.SH': '上证50'
        }
    
    # 构建表格内容
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #333; margin-bottom: 30px; }
        .date { text-align: center; color: #666; margin-bottom: 30px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #4a90e2; color: white; font-weight: bold; }
        tr:hover { background: #f5f9ff; }
        .signal-buy { color: #e74c3c; font-weight: bold; }
        .signal-sell { color: #27ae60; font-weight: bold; }
        .signal-hold { color: #95a5a6; font-weight: bold; }
        .confidence { background: #e8f4f8; padding: 2px 8px; border-radius: 3px; }
        .summary { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .summary h3 { margin-top: 0; color: #333; }
        .position-guide { background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107; }
        .position-guide h4 { margin-top: 0; color: #856404; }
        .footer { text-align: center; color: #999; margin-top: 30px; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>[REPORT] 股市每日投资报告</h1>
        <p class="date">生成时间: """ + datetime.now().strftime('%Y年%m月%d日 %H:%M:%S') + """</p>
        
        <div class="summary">
            <h3>[OVERVIEW] 市场概览</h3>
            <p>今日市场情绪：""" + get_market_sentiment(signals_data) + """</p>
            <p>建议持仓比例：""" + get_recommended_position(signals_data) + """</p>
        </div>
        
        <div class="position-guide">
            <h4>[POSITION] 仓位分配建议</h4>
            <p>""" + get_position_allocation(signals_data) + """</p>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>指数代码</th>
                    <th>指数名称</th>
                    <th>信号</th>
                    <th>信心度</th>
                    <th>多因子评分</th>
                    <th>ML预测</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # 添加每个指数的信号
    for ts_code, data in signals_data.items():
        name = indices_info.get(ts_code, ts_code)
        signal = data.get('signal', 'HOLD')
        confidence = data.get('confidence', 0)
        factor_score = data.get('factor_score', 'N/A')
        ml_prediction = data.get('ml_prediction', 'N/A')
        
        signal_class = f'signal-{signal.lower()}'
        signal_text = signal
        
        if signal == 'BUY':
            signal_display = f'<span class="{signal_class}">📈 买入</span>'
        elif signal == 'SELL':
            signal_display = f'<span class="{signal_class}">📉 卖出</span>'
        else:
            signal_display = f'<span class="{signal_class}">⏸️ 持有</span>'
        
        html += f"""
                <tr>
                    <td>{ts_code}</td>
                    <td>{name}</td>
                    <td>{signal_display}</td>
                    <td><span class="confidence">{confidence:.1%}</span></td>
                    <td>{factor_score}</td>
                    <td>{ml_prediction}</td>
                </tr>
        """
    
    html += """
            </tbody>
        </table>
        
        <div class="footer">
            <p>本报告由股票分析系统自动生成</p>
            <p>数据来源: Tushare Pro | 分析模型: 多因子 + XGBoost集成</p>
            <p>免责声明: 本报告仅供参考，不构成投资建议</p>
        </div>
    </div>
</body>
</html>
    """
    
    return html


def get_market_sentiment(signals_data):
    """获取市场情绪"""
    if not signals_data:
        return "数据不足"
    
    buy_count = sum(1 for d in signals_data.values() if d.get('signal') == 'BUY')
    sell_count = sum(1 for d in signals_data.values() if d.get('signal') == 'SELL')
    hold_count = sum(1 for d in signals_data.values() if d.get('signal') == 'HOLD')
    
    total = len(signals_data)
    if buy_count > total * 0.5:
        return "[BULLISH] 看涨情绪主导，建议积极建仓"
    elif sell_count > total * 0.5:
        return "[BEARISH] 看跌情绪主导，建议减仓观望"
    elif hold_count > total * 0.5:
        return "[WAIT] 市场观望情绪浓厚，建议保持仓位"
    else:
        return "[UNCERTAIN] 市场分歧明显，建议谨慎操作"


def get_recommended_position(signals_data):
    """获取推荐持仓比例"""
    if not signals_data:
        return "数据不足"
    
    buy_count = sum(1 for d in signals_data.values() if d.get('signal') == 'BUY')
    sell_count = sum(1 for d in signals_data.values() if d.get('signal') == 'SELL')
    
    if buy_count >= 3:
        return "80% - 90% (积极持仓)"
    elif buy_count >= 1 and sell_count <= 1:
        return "50% - 70% (平衡持仓)"
    elif sell_count >= 2:
        return "20% - 40% (谨慎持仓)"
    else:
        return "40% - 60% (中性持仓)"


def get_position_allocation(signals_data):
    """获取仓位分配建议"""
    if not signals_data:
        return "数据不足，无法生成仓位建议"
    
    allocation = []
    for ts_code, data in signals_data.items():
        signal = data.get('signal', 'HOLD')
        confidence = data.get('confidence', 0)
        
        if signal == 'BUY':
            if confidence >= 0.8:
                allocation.append(f"[HIGH] {ts_code}: 20% (高信心买入)")
            elif confidence >= 0.6:
                allocation.append(f"[MEDIUM] {ts_code}: 15% (中等信心买入)")
            else:
                allocation.append(f"[LOW] {ts_code}: 10% (低信心买入)")
        elif signal == 'SELL':
            allocation.append(f"[SELL] {ts_code}: 清仓> (卖出信号)")
    
    if allocation:
        return '\n'.join(allocation)
    else:
        return "当前无明确买入信号，建议保持现金仓位 or 减仓持有"


def run_daily_workflow(to_emails=None):
    """
    运行每日全流程：数据同步 → 信号分析 → 报表生成 → 邮件推送
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
            timeout=300
        )
        if result.returncode == 0:
            print("[OK] 数据同步成功")
        else:
            print(f"[WARNING] 数据同步警告: {result.stderr}")
    except Exception as e:
        print(f"[ERROR] 数据同步失败: {str(e)}")
        return
    
    # 2. 信号分析
    print("\n[STEP 2] 分析数据生成信号...")
    print("-" * 40)
    try:
        from analysis.index_analyzer import signal_all_indices
        signal_all_indices()
        
        # 生成持仓建议报告
        print("\n[步骤2.1] 生成持仓建议报告...")
        try:
            from analysis.index_analyzer import IndexAnalyzer
            from active_skills.stock_signal_generator.position_advisor import (
                calculate_position_score, get_position_advice, generate_position_report
            )
            from entity import constant
            from analysis.signal_generator import SignalGenerator
            
            # 加载所有指数信号数据（调用 analyze 以生成 final_signal）
            signals = {}
            for code in constant.TS_CODE_NAME_DICT.keys():
                analyzer = IndexAnalyzer(code)
                analyzer.analyze(include_ml=True)  # 关键：必须调用 analyze() 生成 final_signal
                if len(analyzer.data) > 0 and 'final_signal' in analyzer.data.columns:
                    signals[code] = {
                        'total_rows': len(analyzer.data),
                        'buy_signals': len(analyzer.data[analyzer.data['final_signal']=='BUY']),
                        'sell_signals': len(analyzer.data[analyzer.data['final_signal']=='SELL']),
                        'hold_signals': len(analyzer.data[analyzer.data['final_signal']=='HOLD'])
                    }
            
            if signals:
                # 计算仓位建议
                df_score = calculate_position_score(signals)
                df_advice = get_position_advice(df_score)
                report = generate_position_report(df_advice)
                
                # 保存到文件
                import os
                os.makedirs('records', exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                report_file = f'records/持仓建议报告_{timestamp}.txt'
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"[OK] 持仓建议报告已保存: {report_file}")
            else:
                print("[WARNING] 无信号数据可生成持仓建议")
        except Exception as e:
            print(f"[WARNING] 持仓建议生成失败: {e}")
        
        print("[OK] 信号分析完成")
    except Exception as e:
        print(f"[ERROR] 信号分析失败: {str(e)}")
        return
    
    # 3. 生成HTML报表
    print("\n[STEP 3] 生成HTML报表...")
    print("-" * 40)
    try:
        # 使用report_generator模块生成报表
        import report_generator
        report_file, html_content = report_generator.save_html_report()  # 保存返回的report_file
        print("[OK] HTML报表已生成: " + report_file)
    except Exception as e:
        print(f"[ERROR] 报表生成失败: {str(e)}")
        return
    
    # 4. 发送邮件
    if to_emails:
        print(f"\n[STEP 4] 发送邮件至 {to_emails}...")
        print("-" * 40)
        
        # 发送邮件功能
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email.mime.text import MIMEText
        from email.utils import formatdate
        from email import encoders
        import os
        
        success = False
        
        try:
            # 邮件配置
            smtp_server = "smtp.163.com"
            smtp_port = 465
            smtp_user = "workhardliuzheng@163.com"
            smtp_password = "UBnHVwGi2QG3JEA2"  # 客户端授权码
            
            # 构建邮件
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = to_emails
            msg['Date'] = formatdate(localtime=True)
            msg['Subject'] = "[A股投资顾问] " + datetime.now().strftime('%Y-%m-%d') + " 市场分析报告"
            
            # 邮件正文
            body = MIMEText("股市分析系统每日报告，请查看附件HTML文件。", 'plain', 'utf-8')
            msg.attach(body)
            
            # 读取HTML报表
            # 使用report_generator返回的report_file（绝对路径）
            report_path = report_file  # 直接使用返回的绝对路径
            if os.path.exists(report_path):
                with open(report_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="daily_report_{datetime.now().strftime("%Y%m%d")}.html"')
                    msg.attach(part)
                
                # 发送邮件
                with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_user, to_emails.split(','), msg.as_string())
                
                print("[OK] 邮件发送成功")
                success = True
            else:
                print("[WARNING] HTML报表未生成，跳过邮件发送: " + report_path)
        except Exception as e:
            print(f"[ERROR] 邮件发送失败: {str(e)}")
        
        if not success:
            print("[WARNING] 邮件发送未成功，但不影响其他流程")
    
    print("\n" + "=" * 60)
    print("[DONE] 每日工作流完成！")
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
    args = parser.parse_args()
    
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
            model_type=args.model_type,
            feature_selection=args.feature_selection
        )
    
    elif args.mode == 'daily_report':
        run_daily_workflow(args.to_emails)
    
    elif args.mode == 'backtest':
        from analysis.index_analyzer import backtest_all_indices
        # 支持多个指数，用逗号分隔
        codes = args.ts_code.split(',') if args.ts_code else None
        backtest_all_indices(
            ts_code=codes,
            strategy=args.strategy,
            include_ml=not args.no_ml,
            auto_tune=args.auto_tune,
            model_type=args.model_type,
            commission_rate=args.commission,
            execution_timing=args.execution_timing,
            feature_selection=args.feature_selection
        )
