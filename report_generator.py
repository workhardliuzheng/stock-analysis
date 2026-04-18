"""
向后兼容 shim - 实际实现在 report/ 包中

供 main.py 的 run_daily_workflow() 调用:
    import report_generator
    report_generator.save_html_report()
"""

from report.report_generator import UnifiedReportGenerator


def save_html_report(signals_list=None):
    """
    生成 HTML 报告并保存到文件。

    Args:
        signals_list: 信号数据列表，如果为 None 则内部运行分析

    Returns:
        tuple: (filepath, html_content)
    """
    gen = UnifiedReportGenerator()
    return gen.save_html_report(signals_list=signals_list)
