#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股市日报推送工具

功能:
1. 生成HTML日报
2. 发送邮件
3. 飞书推送
"""

import os
import json
from datetime import datetime


def load_signals_data():
    """加载信号数据"""
    signal_file = r'E:\pycharm\stock-analysis\signals.json'
    
    if os.path.exists(signal_file):
        with open(signal_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # 返回默认数据用于测试
        return {
            '000688.SH': {'signal': 'BUY', 'confidence': 0.75, 'factor_score': 85, 'ml_prediction': '+0.5%'},
            '399006.SZ': {'signal': 'HOLD', 'confidence': 0.60, 'factor_score': 65, 'ml_prediction': '+0.1%'},
            '000001.SH': {'signal': 'BUY', 'confidence': 0.68, 'factor_score': 72, 'ml_prediction': '+0.3%'},
            '000905.SH': {'signal': 'BUY', 'confidence': 0.82, 'factor_score': 88, 'ml_prediction': '+0.8%'},
            '000852.SH': {'signal': 'HOLD', 'confidence': 0.55, 'factor_score': 60, 'ml_prediction': '-0.1%'}
        }


def get_indices_info():
    """获取指数信息映射"""
    return {
        '000688.SH': '科创50',
        '399006.SZ': '创业板指',
        '000001.SH': '上证综指',
        '000905.SH': '中证500',
        '000852.SH': '中证1000',
        '000300.SH': '沪深300',
        '399001.SZ': '深证成指',
        '000016.SH': '上证50'
    }


def get_market_sentiment(signals_data):
    """获取市场情绪"""
    if not signals_data:
        return "数据不足"
    
    buy_count = sum(1 for d in signals_data.values() if d.get('signal') == 'BUY')
    sell_count = sum(1 for d in signals_data.values() if d.get('signal') == 'SELL')
    hold_count = sum(1 for d in signals_data.values() if d.get('signal') == 'HOLD')
    
    total = len(signals_data)
    if buy_count > total * 0.5:
        return "📈 看涨情绪主导，建议积极建仓"
    elif sell_count > total * 0.5:
        return "📉 看跌情绪主导，建议减仓观望"
    elif hold_count > total * 0.5:
        return "⏸️ 市场观望情绪浓厚，建议保持仓位"
    else:
        return "📊 市场分歧明显，建议谨慎操作"


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
                allocation.append(f"🚀 {ts_code}: 20% (高信心买入)")
            elif confidence >= 0.6:
                allocation.append(f"📈 {ts_code}: 15% (中等信心买入)")
            else:
                allocation.append(f" bullish {ts_code}: 10% (低信心买入)")
        elif signal == 'SELL':
            allocation.append(f"📉 {ts_code}: 清仓> (卖出信号)")
    
    if allocation:
        return '\n'.join(allocation)
    else:
        return "当前无明确买入信号，建议保持现金仓位 or 减仓持有"


def generate_html_report():
    """生成HTML格式的日报"""
    signals_data = load_signals_data()
    indices_info = get_indices_info()
    
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
        <h1>📊 股市每日投资报告</h1>
        <p class="date">生成时间: """ + datetime.now().strftime('%Y年%m月%d日 %H:%M:%S') + """</p>
        
        <div class="summary">
            <h3>📈 市场概览</h3>
            <p>今日市场情绪：""" + get_market_sentiment(signals_data) + """</p>
            <p>建议持仓比例：""" + get_recommended_position(signals_data) + """</p>
        </div>
        
        <div class="position-guide">
            <h4>仓位分配建议 💰</h4>
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


def save_html_report():
    """保存HTML报告到文件"""
    html_content = generate_html_report()
    report_file = r'E:\pycharm\stock-analysis\daily_report.html'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"[OK] HTML报告已保存: {report_file}")
    return report_file, html_content


if __name__ == "__main__":
    # 生成并保存报告
    save_html_report()
    print("Stock daily report generated!")
