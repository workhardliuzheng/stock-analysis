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

    def generate(self, signals_list: list) -> ReportResult:
        """
        主入口：生成 HTML + 文本报告并保存。

        Args:
            signals_list: list of dict，每个 dict 来自 IndexAnalyzer.get_current_signal()

        Returns:
            ReportResult: 包含 html, text, 文件路径, 市场概览
        """
        overview = self._build_market_overview(signals_list)
        advice_list = self._build_position_advice(signals_list)
        advice_text = self._build_investment_advice(signals_list, overview)
        risk_text = self._build_risk_text(overview)

        html = self.generate_html(signals_list, overview, advice_list, advice_text, risk_text)
        text = self.generate_text(signals_list, overview, advice_list)

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
                      risk_text: str = None) -> str:
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
            'signal_table_html': render_signal_table(signals_list),
            'position_guide_html': render_position_guide(advice_list),
            'advice_html': render_advice_section(advice_text) + render_risk_section(risk_text),
        }
        return render_full_report(context)

    def generate_text(self, signals_list: list,
                      overview: dict = None,
                      advice_list: list = None) -> str:
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
