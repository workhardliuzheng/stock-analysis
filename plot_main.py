"""
作图入口

使用 IndexAnalyzer 生成6种分析图表：
1. 价格与均线全景图
2. 偏离率与历史百分位图
3. MACD分析图
4. 成交量历史百分位图
5. 估值指标对比图
6. 综合技术指标面板
"""
import argparse

from entity import constant
from analysis.index_analyzer import IndexAnalyzer


def plot_all(save_dir=None, show=False):
    """
    为所有指数生成图表
    
    Args:
        save_dir: 图表保存目录，默认使用 constant.DEFAULT_FILE_PATH
        show: 是否显示图表
    """
    for ts_code in constant.TS_CODE_LIST:
        name = constant.TS_CODE_NAME_DICT.get(ts_code, ts_code)
        print('=' * 50)
        print(f'生成 {name} ({ts_code}) 图表...')
        print('=' * 50)
        
        try:
            analyzer = IndexAnalyzer(ts_code)
            analyzer.analyze()
            analyzer.print_current_status()
            analyzer.generate_charts(save_dir=save_dir, show=show)
        except Exception as e:
            print(f'生成 {ts_code} 图表失败: {e}')
    
    print('=' * 50)
    print('所有图表生成完成！')
    print('=' * 50)


def plot_single(ts_code, save_dir=None, show=False):
    """
    为单个指数生成图表
    
    Args:
        ts_code: 指数代码
        save_dir: 图表保存目录
        show: 是否显示图表
    """
    name = constant.TS_CODE_NAME_DICT.get(ts_code, ts_code)
    print(f'生成 {name} ({ts_code}) 图表...')
    
    analyzer = IndexAnalyzer(ts_code)
    analyzer.analyze()
    analyzer.print_current_status()
    analyzer.generate_charts(save_dir=save_dir, show=show)
    
    print(f'{name} 图表生成完成！')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='股票分析系统 - 图表生成')
    parser.add_argument('--ts-code', help='指定指数代码（不指定则生成所有指数图表）')
    parser.add_argument('--save-dir', help='图表保存目录')
    parser.add_argument('--show', action='store_true', help='显示图表')
    args = parser.parse_args()
    
    if args.ts_code:
        plot_single(args.ts_code, save_dir=args.save_dir, show=args.show)
    else:
        plot_all(save_dir=args.save_dir, show=args.show)
