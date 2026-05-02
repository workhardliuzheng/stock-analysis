"""
统一报告生成器

基于 IndexAnalyzer.get_current_signal() 输出的信号数据，
生成 HTML 和纯文本格式的投资报告。

供 main.py daily_report 流程和 active_skills 共同使用。
"""

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

# 确保项目根目录在 path 中
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from report.html_templates import (
    render_full_report,
    render_market_summary,
    render_signal_table,
    render_portfolio_summary,
    render_position_guide,
    render_advice_section,
    render_risk_section,
)


@dataclass
class ReportResult:
    """报告生成结果"""
    html: str = ''
    text: str = ''
    html_path: str = ''
    text_path: str = ''
    market_overview: dict = field(default_factory=dict)


class UnifiedReportGenerator:
    """
    统一报告生成器

    接收信号数据列表 (来自 IndexAnalyzer.get_current_signal())，
    生成 HTML + 纯文本两种格式的投资报告并保存到文件。
    """

    def __init__(self, output_dir: str = None):
        """
        Args:
            output_dir: 报告输出目录，默认从 config.yaml 读取或使用 'reports'
        """
        if output_dir is None:
            try:
                from util.config_loader import get_report_config
                output_dir = get_report_config().get('output_dir', 'reports')
            except Exception:
                output_dir = 'reports'

        # 如果是相对路径，基于项目根目录
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(_project_root, output_dir)

        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    # ==================== 公开接口 ====================

    def generate(self, signals_list: list, update_portfolio: bool = True) -> ReportResult:
        """
        主入口：生成 HTML + 文本报告并保存。

        Args:
            signals_list: list of dict，每个 dict 来自 IndexAnalyzer.get_current_signal()
            update_portfolio: 是否更新持仓跟踪（首次运行后每天设为 True）

        Returns:
            ReportResult: 包含 html, text, 文件路径, 市场概览, 持仓状态
        """
        # 持仓跟踪
        portfolio_state = []
        portfolio_summary = {}
        if update_portfolio and signals_list:
            try:
                from report.portfolio_tracker import PortfolioTracker
                tracker = PortfolioTracker()
                summary = tracker.daily_update(signals_list)
                portfolio_state = tracker.get_latest_state()
                portfolio_summary = summary
                if summary.get('status') == 'ok':
                    print(f"\n[PORTFOLIO] 持仓更新完成: "
                          f"仓位 {summary['position_pct']:.1f}% / "
                          f"买{summary['buy_count']}卖{summary['sell_count']}")
            except Exception as e:
                print(f"[WARNING] 持仓跟踪更新失败: {e}")

        overview = self._build_market_overview(signals_list)
        advice_list = self._build_position_advice(signals_list)
        advice_text = self._build_investment_advice(signals_list, overview)
        risk_text = self._build_risk_text(overview)

        html = self.generate_html(signals_list, overview, advice_list, advice_text, risk_text,
                                  portfolio_state=portfolio_state)
        text = self.generate_text(signals_list, overview, advice_list,
                                  portfolio_state=portfolio_state)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_path = os.path.join(self.output_dir, f'daily_report_{timestamp}.html')
        text_path = os.path.join(self.output_dir, f'daily_report_{timestamp}.txt')

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text)

        print(f"[OK] HTML 报告已保存: {html_path}")
        print(f"[OK] 文本报告已保存: {text_path}")

        return ReportResult(
            html=html,
            text=text,
            html_path=html_path,
            text_path=text_path,
            market_overview=overview,
        )

    def generate_html(self, signals_list: list,
                      overview: dict = None,
                      advice_list: list = None,
                      advice_text: str = None,
                      risk_text: str = None,
                      portfolio_state: list = None) -> str:
        """生成 HTML 报告字符串。"""
        if overview is None:
            overview = self._build_market_overview(signals_list)
        if advice_list is None:
            advice_list = self._build_position_advice(signals_list)
        if advice_text is None:
            advice_text = self._build_investment_advice(signals_list, overview)
        if risk_text is None:
            risk_text = self._build_risk_text(overview)

        context = {
            'title': '[REPORT] 股市每日投资报告',
            'generated_at': datetime.now().strftime('%Y年%m月%d日 %H:%M:%S'),
            'market_summary_html': render_market_summary(overview),
            'portfolio_html': render_portfolio_summary(portfolio_state) if portfolio_state else '',
            'signal_table_html': render_signal_table(signals_list),
            'position_guide_html': render_position_guide(advice_list),
            'advice_html': render_advice_section(advice_text) + render_risk_section(risk_text),
        }
        return render_full_report(context)

    # ==================== 用户实际持仓集成 ====================

    def _build_price_map(self, signals_list: list) -> tuple:
        """
        从信号列表构建价格映射。

        Returns:
            (price_by_code, price_by_name):
                price_by_code: {ts_code: close_price}
                price_by_name: {name: close_price} 用于名称模糊匹配
        """
        price_by_code = {}
        price_by_name = {}
        for sig in signals_list:
            code = sig.get('ts_code', '')
            name = sig.get('name', '')
            close = sig.get('close')
            if close is not None:
                price_by_code[code] = close
                price_by_name[name] = close
                # 去掉空格，增加匹配成功率
                price_by_name[name.replace(' ', '')] = close
        return price_by_code, price_by_name

    def _build_user_positions_text(self, signals_list: list) -> str:
        """
        读取 position_tracker 中的实际持仓，生成日报文本段。

        Args:
            signals_list: 信号数据，用于构建价格映射和信号映射

        Returns:
            str: 日报持仓段文本，无持仓时返回空字符串
        """
        try:
            from position_tracker import PositionTracker

            tracker = PositionTracker()
            positions = tracker.get_current_positions()
            if not positions:
                return ''

            price_by_code, price_by_name = self._build_price_map(signals_list)

            # 构建当前价格映射 (代码匹配 -> 名称模糊匹配)
            current_prices = {}
            for p in positions:
                code = p['code']
                name = p['name']
                if code in price_by_code:
                    current_prices[code] = price_by_code[code]
                elif code in price_by_name:
                    current_prices[code] = price_by_name[code]
                else:
                    # 名称子串匹配: "沪深300ETF" -> 信号名包含"沪深300"
                    matched = False
                    for sig_name, sig_price in price_by_name.items():
                        if name and sig_name and (name in sig_name or sig_name in name):
                            current_prices[code] = sig_price
                            matched = True
                            break
                    if not matched:
                        # 尝试用 code 匹配 name (tushare返回的信号code可能是ETF代码)
                        for sig_code, sig_price in price_by_code.items():
                            last_part = sig_code.split('.')[0]
                            if last_part in code or code in last_part:
                                current_prices[code] = sig_price
                                break

            # 获取日报摘要
            summary = tracker.get_daily_summary(current_prices)

            # 构建信号映射 (信号名称 -> 信号类型)
            signal_map = {}
            for sig in signals_list:
                sname = sig.get('name', '')
                signal_map[sname] = sig.get('final_signal', 'HOLD')

            # 可转债推荐列表 (当前持仓中的可转债)
            cb_codes = [p['code'] for p in positions if p['type'] == '可转债']

            # 匹配操作建议
            advices = tracker.match_signals(summary, signal_map, cb_codes)

            # ====== 输出文本 ======
            lines = []
            lines.append("")
            lines.append("[POSITIONS] 投资账户日报")
            lines.append("-" * 50)

            total_cost = summary['total_cost']
            current_value = summary['current_value']
            unrealized = summary['unrealized_pnl']
            realized = tracker.get_realized_pnl()
            total_pnl = unrealized + realized
            total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0

            dv = current_value - total_cost  # 浮动盈亏(与成本比)
            dv_pct = (dv / total_cost * 100) if total_cost > 0 else 0.0

            lines.append(f"  总投入: RMB {total_cost:>10,.2f}")
            lines.append(f"  当前净值: RMB {current_value:>10,.2f}")
            lines.append(f"  浮动盈亏: {dv:+,.2f} ({dv_pct:+.2f}%)")
            lines.append(f"  已实现盈亏: {realized:+,.2f}")
            lines.append(f"  总 盈 亏: {total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)")

            # 持仓明细表头
            lines.append("")
            lines.append(f"  {'品种':<6} {'名称':<12} {'代码':<8} {'买入日期':<12} "
                        f"{'成本价':>8} {'数量':>8} {'市价':>8} {'盈亏':>12} {'操作':>10}")
            lines.append(f"  {'-'*6} {'-'*12} {'-'*8} {'-'*12} "
                        f"{'-'*8} {'-'*8} {'-'*8} {'-'*12} {'-'*10}")

            for p in positions:
                ptype = p['type']
                name = p['name']
                code = p['code']
                buy_date = p['buy_date']
                buy_price = float(p['buy_price'])
                qty = float(p['quantity'])
                curr_price = current_prices.get(code, buy_price)
                dv2 = (curr_price - buy_price) * qty
                dv2_pct = (curr_price - buy_price) / buy_price * 100

                # 从建议中获取操作标签
                action_label = '-'
                for a in advices:
                    if a['code'] == code:
                        action_label = a['action'][:10]
                        break

                lines.append(f"  {ptype:<6} {name:<12} {code:<8} {buy_date:<12} "
                            f"{buy_price:>8.3f} {qty:>8.0f} {curr_price:>8.3f} "
                            f"{dv2:>+,.2f} {action_label:>10}")

            # 操作建议
            if advices:
                lines.append("")
                lines.append("  [操作建议]")
                for a in advices:
                    action = a['action']
                    reason = a['reason']
                    lines.append(f"  - {a['name']} ({a['code']}): {action} — {reason}")

            return "\n".join(lines)

        except ImportError:
            # position_tracker 未安装 / 尚未创建
            return ''
        except Exception as e:
            return f"\n\n[WARNING] 持仓信息读取失败: {e}"

    def generate_text(self, signals_list: list,
                      overview: dict = None,
                      advice_list: list = None,
                      portfolio_state: list = None) -> str:
        """生成纯文本报告字符串。"""
        if overview is None:
            overview = self._build_market_overview(signals_list)
        if advice_list is None:
            advice_list = self._build_position_advice(signals_list)

        lines = []
        lines.append("=" * 70)
        lines.append("[OK] 股市分析系统 - 每日投资报告")
        lines.append(f"[OK] 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)

        # 持仓概览（新！）
        if portfolio_state:
            lines.append("")
            lines.append("[PORTFOLIO] 持仓概览")
            lines.append("-" * 40)
            total_pct = float(portfolio_state[0].get('total_position_pct', 0))
            cash_pct = float(portfolio_state[0].get('cash_pct', 0))
            total_mv = float(portfolio_state[0].get('total_market_value', 0))
            lines.append(f"  总仓位: {total_pct:.1f}%  |  现金: {cash_pct:.1f}%  |  总市值: RMB{total_mv:,.2f}")
            # 今日操作
            ops = [r for r in portfolio_state if r.get('action') not in ('持有', None, 'INIT')]
            if ops:
                lines.append("  今日操作:")
                for r in ops:
                    action = r.get('action', '')
                    val = abs(float(r.get('action_value', 0)))
                    name = r.get('name', '')
                    new_w = float(r.get('new_weight_pct', 0))
                    if r.get('action_value', 0) > 0:
                        lines.append(f"    {name}  {action} +RMB{val:>8.2f}  -> 权重{new_w:.1f}%")
                    else:
                        lines.append(f"    {name}  {action} -RMB{val:>8.2f}  -> 权重{new_w:.1f}%")
            lines.append("")
            # 持仓明细表
            lines.append(f"  {'指数':8s} {'权重':>6s} {'市值':>10s} {'成本':>10s} {'收益':>7s} {'信号':>6s}")
            lines.append("  " + "-" * 53)
            for r in portfolio_state:
                name = r.get('name', '')[:8]
                w = float(r.get('weight_pct', 0))
                mv = float(r.get('market_value', 0))
                cost = float(r.get('cost_basis', 0))
                ret = float(r.get('return_pct', 0))
                sig = r.get('current_signal', '')
                lines.append(f"  {name:8s} {w:>5.1f}% RMB{mv:>8,.0f} RMB{cost:>8,.0f} {ret:>+6.2f}% {sig:>6s}")
            lines.append("")

        # 市场概览
        lines.append("")
        lines.append("[OVERVIEW] 市场概览")
        lines.append("-" * 40)
        lines.append(f"  市场情绪: {overview.get('sentiment', '数据不足')}")
        lines.append(f"  平均信号强度: {overview.get('avg_strength', 0):.1f}")
        lines.append(f"  信号统计: BUY={overview.get('buy_count', 0)} / "
                     f"SELL={overview.get('sell_count', 0)} / "
                     f"HOLD={overview.get('hold_count', 0)}")
        lines.append(f"  建议持仓比例: {overview.get('recommended_position', '待计算')}")

        # 信号明细
        lines.append("")
        lines.append("[SIGNAL] 各指数信号明细")
        lines.append("-" * 40)
        header = f"  {'指数':<12} {'信号':<8} {'置信度':<8} {'评分':<8} {'趋势':<8} {'ML预测':<10} {'涨跌幅':<8}"
        lines.append(header)
        lines.append("  " + "-" * 68)

        for sig in signals_list:
            name = sig.get('name', sig.get('ts_code', ''))[:10]
            signal = sig.get('final_signal', 'HOLD')
            confidence = sig.get('final_confidence', 0)
            factor_score = sig.get('factor_score', 0)
            trend_map = {'uptrend': '上升', 'downtrend': '下降', 'sideways': '震荡'}
            trend = trend_map.get(sig.get('trend_state', ''), 'N/A')
            ml_ret = sig.get('ml_predicted_return', 0)
            ml_display = f"{ml_ret:+.3f}%" if ml_ret is not None else "N/A"
            pct_chg = sig.get('pct_chg', 0)

            lines.append(f"  {name:<12} {signal:<8} {confidence:<8.1%} "
                        f"{factor_score:<8.1f} {trend:<8} {ml_display:<10} {pct_chg:+.2f}%")

        # 持仓建议
        lines.append("")
        lines.append("[POSITION] 持仓建议")
        lines.append("-" * 40)
        for adv in advice_list:
            lines.append(f"  {adv['name']}: {adv['operation_text']} | "
                        f"建议仓位 {adv['position_pct']:.0f}% | "
                        f"风险: {adv['risk_level']} | {adv['reason']}")

        # 实际持仓 (用户通过 position_tracker 记录的真实持仓)
        user_positions = self._build_user_positions_text(signals_list)
        if user_positions:
            lines.append(user_positions)

        # 风险提示
        lines.append("")
        lines.append("[RISK] 风险提示")
        lines.append("-" * 40)
        lines.append("  本报告由自动化系统生成，仅供参考，不构成投资建议。")
        lines.append("  投资有风险，入市需谨慎。")

        lines.append("")
        lines.append("=" * 70)
        return "\n".join(lines)

    def save_html_report(self, signals_list: list = None) -> tuple:
        """
        向后兼容接口。

        如果未传 signals_list，内部运行分析生成信号数据。

        Returns:
            tuple: (filepath, html_content)
        """
        if signals_list is None:
            signals_list = self._run_analysis()

        result = self.generate(signals_list)
        return result.html_path, result.html

    # ==================== 内部方法 ====================

    def _run_analysis(self) -> list:
        """内部运行分析获取信号数据（向后兼容用）"""
        from entity import constant
        from analysis.index_analyzer import IndexAnalyzer

        signals_list = []
        for code in constant.TS_CODE_NAME_DICT.keys():
            try:
                analyzer = IndexAnalyzer(code)
                analyzer.analyze(include_ml=True)
                sig = analyzer.get_current_signal()
                if sig:
                    signals_list.append(sig)
            except Exception as e:
                print(f"[WARNING] 分析 {code} 失败: {e}")
        return signals_list

    def _build_market_overview(self, signals_list: list) -> dict:
        """构建市场概览数据。"""
        if not signals_list:
            return {
                'sentiment': '数据不足',
                'avg_strength': 0,
                'buy_count': 0, 'sell_count': 0, 'hold_count': 0,
                'recommended_position': '数据不足',
            }

        buy_count = sum(1 for s in signals_list if s.get('final_signal') == 'BUY')
        sell_count = sum(1 for s in signals_list if s.get('final_signal') == 'SELL')
        hold_count = sum(1 for s in signals_list if s.get('final_signal') == 'HOLD')
        total = len(signals_list)

        # 平均 factor_score 作为信号强度代理
        scores = [s.get('factor_score', 50) for s in signals_list]
        avg_score = sum(scores) / len(scores) if scores else 50
        avg_strength = avg_score - 50  # 归一化到 -50 ~ +50

        # 市场情绪判断
        if buy_count >= total * 0.6:
            sentiment = '强烈看涨 - 市场普遍看多'
        elif buy_count > sell_count:
            sentiment = '偏多 - 买入信号占优'
        elif sell_count >= total * 0.6:
            sentiment = '强烈看跌 - 市场普遍看空'
        elif sell_count > buy_count:
            sentiment = '偏空 - 卖出信号占优'
        else:
            sentiment = '震荡 - 多空分歧'

        # 推荐仓位
        if buy_count >= total * 0.6:
            recommended_position = '70% - 90% (积极持仓)'
        elif buy_count > sell_count:
            recommended_position = '50% - 70% (平衡持仓)'
        elif sell_count >= total * 0.6:
            recommended_position = '10% - 30% (防御持仓)'
        elif sell_count > buy_count:
            recommended_position = '20% - 40% (谨慎持仓)'
        else:
            recommended_position = '40% - 60% (中性持仓)'

        return {
            'sentiment': sentiment,
            'avg_strength': avg_strength,
            'buy_count': buy_count,
            'sell_count': sell_count,
            'hold_count': hold_count,
            'recommended_position': recommended_position,
        }

    def _build_position_advice(self, signals_list: list) -> list:
        """
        构建每个指数的持仓建议。

        评分逻辑复用 active_skills/.../position_advisor.py 的算法：
        - 信号强度分 (0-40): 基于 factor_score
        - 置信度分 (0-30): 基于 final_confidence
        - 趋势分 (0-30): 基于 trend_state
        """
        advice_list = []
        for sig in signals_list:
            factor_score = sig.get('factor_score', 50)
            confidence = sig.get('final_confidence', 0.5)
            trend_state = sig.get('trend_state', 'sideways')
            final_signal = sig.get('final_signal', 'HOLD')

            # 信号强度分 (0-40): factor_score 0-100 映射到 0-40
            strength_score = factor_score * 0.4

            # 置信度分 (0-30): confidence 0-1 映射到 0-30
            confidence_score = confidence * 30

            # 趋势分 (0-30)
            trend_scores = {'uptrend': 30, 'sideways': 15, 'downtrend': 5}
            trend_score = trend_scores.get(trend_state, 15)

            total_score = strength_score + confidence_score + trend_score

            # 仓位百分比
            position_pct = min(95, max(5, total_score * 0.95))

            # 操作建议
            if final_signal == 'BUY':
                if confidence >= 0.7:
                    operation_text = '[BUY] 强烈买入'
                else:
                    operation_text = '[BUY] 建议买入'
            elif final_signal == 'SELL':
                if confidence >= 0.7:
                    operation_text = '[SELL] 强烈卖出'
                else:
                    operation_text = '[SELL] 建议卖出'
            else:
                operation_text = '[HOLD] 持有观望'

            # 理由
            trend_map = {'uptrend': '上升趋势', 'downtrend': '下降趋势', 'sideways': '震荡走势'}
            reason = f"评分{factor_score:.0f}, {trend_map.get(trend_state, '未知')}, 置信{confidence:.0%}"

            # 风险等级
            if factor_score > 65 and trend_state == 'uptrend':
                risk_level = '低'
            elif factor_score < 35 and trend_state == 'downtrend':
                risk_level = '高'
            else:
                risk_level = '中'

            advice_list.append({
                'ts_code': sig.get('ts_code', ''),
                'name': sig.get('name', sig.get('ts_code', '')),
                'position_pct': position_pct,
                'operation': final_signal,
                'operation_text': operation_text,
                'reason': reason,
                'risk_level': risk_level,
                'total_score': total_score,
            })

        # 按分数降序排列
        advice_list.sort(key=lambda x: x['total_score'], reverse=True)
        return advice_list

    def _build_investment_advice(self, signals_list: list, overview: dict) -> str:
        """构建投资建议文本 (HTML 格式)。"""
        avg_strength = overview.get('avg_strength', 0)
        buy_count = overview.get('buy_count', 0)
        sell_count = overview.get('sell_count', 0)

        parts = []

        # 总体判断
        if avg_strength > 10:
            parts.append("<p><strong>总体判断: 强烈看涨</strong></p>")
            parts.append(f"<p>建议仓位: 80-90%，策略: 加仓/逢低吸纳</p>")
        elif avg_strength > 0:
            parts.append("<p><strong>总体判断: 偏多</strong></p>")
            parts.append(f"<p>建议仓位: 50-70%，策略: 维持持仓/波段操作</p>")
        elif avg_strength > -10:
            parts.append("<p><strong>总体判断: 震荡</strong></p>")
            parts.append(f"<p>建议仓位: 40-50%，策略: 持仓观察/控制仓位</p>")
        else:
            parts.append("<p><strong>总体判断: 偏空</strong></p>")
            parts.append(f"<p>建议仓位: 20-30%，策略: 减仓/控制风险</p>")

        # 具体建议
        buy_names = [s.get('name', s.get('ts_code', ''))
                     for s in signals_list if s.get('final_signal') == 'BUY']
        sell_names = [s.get('name', s.get('ts_code', ''))
                      for s in signals_list if s.get('final_signal') == 'SELL']

        if buy_names:
            parts.append(f"<p><strong>买入机会:</strong> {', '.join(buy_names)}</p>")
        if sell_names:
            parts.append(f"<p><strong>卖出信号:</strong> {', '.join(sell_names)}</p>")

        return "\n".join(parts) if parts else "<p>暂无明确建议</p>"

    def _build_risk_text(self, overview: dict) -> str:
        """构建风险提示文本 (HTML 格式)。"""
        avg_strength = overview.get('avg_strength', 0)
        parts = []

        if abs(avg_strength) > 15:
            parts.append("<p><strong>[WARNING] 市场情绪极端</strong>，注意反转风险。</p>")
        if overview.get('sell_count', 0) > overview.get('buy_count', 0):
            parts.append("<p>卖出信号多于买入信号，建议控制仓位，严格执行止损。</p>")

        parts.append("<p>本报告由自动化分析系统生成，仅供参考，不构成投资建议。</p>")
        parts.append("<p>投资有风险，入市需谨慎。请结合自身风险承受能力做出决策。</p>")

        return "\n".join(parts)
