"""
HTML 报告模板

提供报告各部分的 HTML 渲染函数。
"""

from datetime import datetime


def render_full_report(context: dict) -> str:
    """
    渲染完整 HTML 报告。

    Args:
        context: {
            'title': str,
            'generated_at': str,
            'market_summary_html': str,
            'position_guide_html': str,
            'signal_table_html': str,
            'advice_html': str,
        }

    Returns:
        完整 HTML 字符串
    """
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #333; margin-bottom: 10px; }}
        .date {{ text-align: center; color: #666; margin-bottom: 30px; }}
        .portfolio {{ background: #e8f5e9; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #4caf50; }}
        .portfolio h3 {{ margin-top: 0; color: #2e7d32; }}
        .action-buy {{ color: #e74c3c; font-weight: bold; }}
        .action-sell {{ color: #27ae60; font-weight: bold; }}
        .return-pos {{ color: #e74c3c; }}
        .return-neg {{ color: #27ae60; }}
        .portfolio-op {{ background: #fff8e1; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        h3 {{ color: #333; margin-top: 25px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #4a90e2; color: white; font-weight: bold; }}
        tr:hover {{ background: #f5f9ff; }}
        .signal-buy {{ color: #e74c3c; font-weight: bold; }}
        .signal-sell {{ color: #27ae60; font-weight: bold; }}
        .signal-hold {{ color: #95a5a6; font-weight: bold; }}
        .confidence {{ background: #e8f4f8; padding: 2px 8px; border-radius: 3px; }}
        .summary {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .summary h3 {{ margin-top: 0; color: #333; }}
        .position-guide {{ background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107; }}
        .position-guide h3 {{ margin-top: 0; color: #856404; }}
        .advice-section {{ background: #d4edda; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745; }}
        .advice-section h3 {{ margin-top: 0; color: #155724; }}
        .risk-section {{ background: #f8d7da; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #dc3545; }}
        .risk-section h3 {{ margin-top: 0; color: #721c24; }}
        .footer {{ text-align: center; color: #999; margin-top: 30px; font-size: 12px; }}
        .metric {{ display: inline-block; background: #e8f4f8; padding: 5px 12px; border-radius: 4px; margin: 3px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{context.get('title', '[REPORT] 股市每日投资报告')}</h1>
        <p class="date">生成时间: {context.get('generated_at', datetime.now().strftime('%Y年%m月%d日 %H:%M:%S'))}</p>

        {context.get('market_summary_html', '')}
        {context.get('portfolio_html', '')}
        {context.get('position_guide_html', '')}
        {context.get('signal_table_html', '')}
        {context.get('advice_html', '')}

        <div class="footer">
            <p>本报告由股票分析系统自动生成</p>
            <p>数据来源: Tushare Pro | 分析模型: 多因子 + XGBoost集成</p>
            <p>免责声明: 本报告仅供参考，不构成投资建议</p>
        </div>
    </div>
</body>
</html>"""


def render_market_summary(overview: dict) -> str:
    """
    渲染市场概览区块。

    Args:
        overview: {
            'sentiment': str,
            'sentiment_icon': str,
            'avg_strength': float,
            'buy_count': int,
            'sell_count': int,
            'hold_count': int,
            'recommended_position': str,
        }
    """
    return f"""
        <div class="summary">
            <h3>[OVERVIEW] 市场概览</h3>
            <p>今日市场情绪: <strong>{overview.get('sentiment', '数据不足')}</strong></p>
            <p>平均信号强度: <span class="metric">{overview.get('avg_strength', 0):.1f}</span></p>
            <p>信号统计:
                <span class="metric signal-buy">BUY: {overview.get('buy_count', 0)}</span>
                <span class="metric signal-sell">SELL: {overview.get('sell_count', 0)}</span>
                <span class="metric signal-hold">HOLD: {overview.get('hold_count', 0)}</span>
            </p>
            <p>建议持仓比例: <strong>{overview.get('recommended_position', '待计算')}</strong></p>
        </div>"""


def render_portfolio_summary(state: list) -> str:
    """
    渲染持仓概览区块。

    Args:
        state: list of dict, 来自 PortfolioTracker.get_latest_state()
    """
    if not state:
        return ''

    total_pct = float(state[0].get('total_position_pct', 0))
    cash_pct = float(state[0].get('cash_pct', 0))
    total_mv = float(state[0].get('total_market_value', 0))
    trade_date = str(state[0].get('trade_date', ''))

    # 今日操作
    ops = [r for r in state if r.get('action') not in ('持有', None, 'INIT')]
    ops_html = ''
    if ops:
        ops_html = '<div class="portfolio-op"><strong>今日操作:</strong><br/>'
        for r in ops:
            action = r.get('action', '')
            val = abs(float(r.get('action_value', 0)))
            name = r.get('name', '')
            new_w = float(r.get('new_weight_pct', 0))
            cls = 'action-buy' if r.get('action_value', 0) > 0 else 'action-sell'
            sign = '+' if r.get('action_value', 0) > 0 else '-'
            ops_html += f'<span class="{cls}">{name} {action} {sign}RMB{val:,.2f} (->{new_w:.1f}%)</span><br/>'
        ops_html += '</div>'

    # 持仓表格行
    rows = ''
    for r in state:
        name = r.get('name', '')
        w = float(r.get('weight_pct', 0))
        mv = float(r.get('market_value', 0))
        cost = float(r.get('cost_basis', 0))
        ret = float(r.get('return_pct', 0))
        sig = r.get('current_signal', '')
        strength = float(r.get('signal_strength', 0))
        ret_cls = 'return-pos' if ret >= 0 else 'return-neg'
        rows += f"""
        <tr>
            <td>{name}</td>
            <td>{w:.1f}%</td>
            <td>RMB{mv:,.0f}</td>
            <td>RMB{cost:,.0f}</td>
            <td class="{ret_cls}">{ret:+.2f}%</td>
            <td>{sig}</td>
            <td>{strength:+.1f}</td>
        </tr>"""

    return f"""
        <div class="portfolio">
            <h3>[PORTFOLIO] 持仓概览 - {trade_date}</h3>
            <p>总仓位: <strong>{total_pct:.1f}%</strong>  |  现金: {cash_pct:.1f}%  |  总市值: <strong>RMB{total_mv:,.2f}</strong></p>
            {ops_html}
            <table>
                <thead><tr>
                    <th>指数</th><th>权重</th><th>市值</th><th>成本</th><th>收益</th><th>信号</th><th>强度</th>
                </tr></thead>
                <tbody>{rows}
                </tbody>
            </table>
        </div>"""


def render_signal_table(signals: list) -> str:
    """
    渲染信号明细表格。

    Args:
        signals: list of dict, 每个 dict 包含:
            ts_code, name, final_signal, final_confidence,
            factor_score, trend_state, ml_predicted_return, ml_signal
    """
    rows = ""
    for sig in signals:
        signal = sig.get('final_signal', 'HOLD')
        signal_class = f'signal-{signal.lower()}'
        signal_map = {'BUY': '[BUY] 买入', 'SELL': '[SELL] 卖出', 'HOLD': '[HOLD] 持有'}
        signal_display = f'<span class="{signal_class}">{signal_map.get(signal, signal)}</span>'

        confidence = sig.get('final_confidence', 0)
        factor_score = sig.get('factor_score', 0)
        trend_state = sig.get('trend_state', 'N/A')
        trend_map = {'uptrend': '上升', 'downtrend': '下降', 'sideways': '震荡'}
        trend_display = trend_map.get(trend_state, trend_state)

        ml_ret = sig.get('ml_predicted_return', 0)
        if ml_ret is not None and not (isinstance(ml_ret, float) and str(ml_ret) == 'nan'):
            ml_display = f"{ml_ret:+.3f}%"
        else:
            ml_display = "N/A"

        ml_signal = sig.get('ml_signal', 'N/A')
        close = sig.get('close', 0)
        pct_chg = sig.get('pct_chg', 0)

        rows += f"""
                <tr>
                    <td>{sig.get('ts_code', '')}</td>
                    <td>{sig.get('name', '')}</td>
                    <td>{close:.2f}</td>
                    <td>{pct_chg:+.2f}%</td>
                    <td>{signal_display}</td>
                    <td><span class="confidence">{confidence:.1%}</span></td>
                    <td>{factor_score:.1f}</td>
                    <td>{trend_display}</td>
                    <td>{ml_display}</td>
                    <td>{ml_signal}</td>
                </tr>"""

    return f"""
        <h3>[SIGNAL] 各指数信号明细</h3>
        <table>
            <thead>
                <tr>
                    <th>指数代码</th>
                    <th>指数名称</th>
                    <th>收盘价</th>
                    <th>涨跌幅</th>
                    <th>信号</th>
                    <th>置信度</th>
                    <th>多因子评分</th>
                    <th>趋势状态</th>
                    <th>ML预测</th>
                    <th>ML信号</th>
                </tr>
            </thead>
            <tbody>{rows}
            </tbody>
        </table>"""


def render_position_guide(advice_list: list) -> str:
    """
    渲染持仓建议区块。

    Args:
        advice_list: list of dict, 每个 dict 包含:
            name, ts_code, position_pct, operation, reason, risk_level
    """
    rows = ""
    for adv in advice_list:
        op = adv.get('operation', 'HOLD')
        op_class = f'signal-{op.lower()}'
        rows += f"""
            <tr>
                <td>{adv.get('name', '')}</td>
                <td><span class="{op_class}">{adv.get('operation_text', op)}</span></td>
                <td><strong>{adv.get('position_pct', 50):.0f}%</strong></td>
                <td>{adv.get('reason', '')}</td>
                <td>{adv.get('risk_level', '中')}</td>
            </tr>"""

    return f"""
        <div class="position-guide">
            <h3>[POSITION] 持仓建议</h3>
            <table>
                <thead>
                    <tr>
                        <th>指数</th>
                        <th>操作建议</th>
                        <th>建议仓位</th>
                        <th>理由</th>
                        <th>风险等级</th>
                    </tr>
                </thead>
                <tbody>{rows}
                </tbody>
            </table>
        </div>"""


def render_advice_section(advice_text: str) -> str:
    """渲染投资建议区块。"""
    return f"""
        <div class="advice-section">
            <h3>[ADVICE] 投资建议</h3>
            <div>{advice_text}</div>
        </div>"""


def render_risk_section(risk_text: str) -> str:
    """渲染风险提示区块。"""
    return f"""
        <div class="risk-section">
            <h3>[RISK] 风险提示</h3>
            <div>{risk_text}</div>
        </div>"""
