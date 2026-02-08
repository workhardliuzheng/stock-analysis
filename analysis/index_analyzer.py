"""
指数技术分析器（重构版）

整合交叉信号检测、历史百分位计算、可视化图表生成
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Dict, List
import warnings
warnings.filterwarnings('ignore')

from entity import constant
from entity.stock_data import StockData
from mysql_connect.sixty_index_mapper import SixtyIndexMapper
from analysis.cross_signal_detector import CrossSignalDetector
from analysis.percentile_calculator import PercentileCalculator
from util.class_util import ClassUtil
from util.date_util import TimeUtils


class IndexAnalyzer:
    """
    指数技术分析器（重构版）
    
    功能：
    1. 计算交叉信号（均线金叉死叉、MACD金叉死叉）
    2. 计算历史百分位（偏离率、成交量、MACD等）
    3. 生成多维度分析图表
    4. 提供当前市场状态摘要
    
    使用示例:
        analyzer = IndexAnalyzer('000001.SH')
        df = analyzer.analyze()
        analyzer.generate_charts(save_path='output/')
        status = analyzer.get_current_status()
    """
    
    def __init__(self, 
                 ts_code: str, 
                 start_date: Optional[str] = None,
                 lookback_years: int = 5):
        """
        初始化指数分析器
        
        Args:
            ts_code: 指数代码
            start_date: 开始日期，默认为5年前
            lookback_years: 百分位计算回溯年数
        """
        self.ts_code = ts_code
        self.lookback_years = lookback_years
        
        # 默认开始日期为回溯年数之前
        if start_date is None:
            start_year = datetime.now().year - lookback_years
            start_date = f"{start_year}0101"
        self.start_date = start_date
        
        # 初始化计算器
        self.cross_detector = CrossSignalDetector()
        self.percentile_calculator = PercentileCalculator(lookback_years=lookback_years)
        
        # 加载数据
        self.mapper = SixtyIndexMapper()
        self.data = self._load_data()
        self.name = constant.TS_CODE_NAME_DICT.get(ts_code, ts_code)
        
        # 图表生成器（延迟加载）
        self._chart_generator = None
    
    def _load_data(self) -> pd.DataFrame:
        """
        从数据库加载指数数据
        
        Returns:
            pd.DataFrame: 指数历史数据
        """
        end_date = TimeUtils.get_current_date_str()
        index_data = self.mapper.select_by_code_and_trade_round(
            self.ts_code, self.start_date, end_date
        )
        
        data_frame_list = []
        for row in index_data:
            stock_data = ClassUtil.create_entities_from_data(StockData, row)
            data_frame_list.append(stock_data.to_dict())
        
        df = pd.DataFrame(data_frame_list)
        
        # 确保trade_date是日期类型并排序
        if 'trade_date' in df.columns and len(df) > 0:
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.sort_values('trade_date').reset_index(drop=True)
        
        return df
    
    def analyze(self) -> pd.DataFrame:
        """
        执行完整分析流程
        
        计算交叉信号和历史百分位，更新DataFrame
        
        Returns:
            pd.DataFrame: 包含分析结果的DataFrame
        """
        if len(self.data) == 0:
            print(f"警告: {self.ts_code} 没有数据")
            return self.data
        
        # 计算交叉信号
        print(f"正在计算 {self.name} 的交叉信号...")
        self.data = self.cross_detector.detect(self.data)
        
        # 计算历史百分位
        print(f"正在计算 {self.name} 的历史百分位...")
        self.data = self.percentile_calculator.calculate(self.data)
        
        return self.data
    
    def get_current_status(self) -> Dict:
        """
        获取当前市场状态摘要
        
        返回最新交易日的所有关键指标状态
        
        Returns:
            Dict: 当前状态字典
        """
        if len(self.data) == 0:
            return {}
        
        latest = self.data.iloc[-1]
        
        status = {
            'ts_code': self.ts_code,
            'name': self.name,
            'trade_date': str(latest.get('trade_date', '')),
            'close': latest.get('close'),
            'pct_chg': latest.get('pct_chg'),
        }
        
        # 均线数据
        status['ma'] = {
            'ma_5': latest.get('ma_5'),
            'ma_10': latest.get('ma_10'),
            'ma_20': latest.get('ma_20'),
            'ma_50': latest.get('ma_50'),
        }
        
        # 交叉信号
        cross_signals = self.cross_detector.parse_signal_json(
            latest.get('cross_signals', '')
        )
        status['cross_signals'] = cross_signals
        
        # 最近金叉死叉日期
        status['latest_golden_cross_ma_5_10'] = self.cross_detector.find_latest_cross_date(
            self.data, 'golden_cross', 'ma_5_10'
        )
        status['latest_death_cross_ma_5_10'] = self.cross_detector.find_latest_cross_date(
            self.data, 'death_cross', 'ma_5_10'
        )
        status['latest_golden_cross_macd'] = self.cross_detector.find_latest_cross_date(
            self.data, 'golden_cross', 'macd'
        )
        status['latest_death_cross_macd'] = self.cross_detector.find_latest_cross_date(
            self.data, 'death_cross', 'macd'
        )
        
        # 百分位数据
        percentile_ranks = self.percentile_calculator.parse_percentile_json(
            latest.get('percentile_ranks', '')
        )
        status['percentile_ranks'] = percentile_ranks
        
        # MACD数据
        status['macd'] = {
            'macd': latest.get('macd'),
            'macd_signal_line': latest.get('macd_signal_line'),
            'macd_histogram': latest.get('macd_histogram'),
        }
        
        # 成交量数据
        status['volume'] = {
            'vol': latest.get('vol'),
            'amount': latest.get('amount'),
        }
        
        # 估值数据
        status['valuation'] = {
            'pe': latest.get('pe'),
            'pb': latest.get('pb'),
            'pe_ttm': latest.get('pe_ttm'),
            'pe_weight': latest.get('pe_weight'),
            'pb_weight': latest.get('pb_weight'),
        }
        
        # RSI/KDJ数据
        status['technical'] = {
            'rsi': latest.get('rsi'),
            'kdj_k': latest.get('kdj_k'),
            'kdj_d': latest.get('kdj_d'),
            'kdj_j': latest.get('kdj_j'),
        }
        
        return status
    
    def print_current_status(self):
        """
        打印当前市场状态摘要
        """
        status = self.get_current_status()
        if not status:
            print(f"{self.ts_code} 无数据")
            return
        
        print(f"\n{'='*60}")
        print(f"  {status['name']} ({status['ts_code']}) 市场状态摘要")
        print(f"{'='*60}")
        print(f"  交易日期: {status['trade_date']}")
        print(f"  收盘价:   {status['close']:.2f}  涨跌幅: {status.get('pct_chg', 0):.2f}%")
        
        # 均线状态
        ma = status.get('ma', {})
        print(f"\n  【均线】")
        print(f"    MA5:  {ma.get('ma_5', 'N/A'):.2f if ma.get('ma_5') else 'N/A'}")
        print(f"    MA10: {ma.get('ma_10', 'N/A'):.2f if ma.get('ma_10') else 'N/A'}")
        print(f"    MA20: {ma.get('ma_20', 'N/A'):.2f if ma.get('ma_20') else 'N/A'}")
        print(f"    MA50: {ma.get('ma_50', 'N/A'):.2f if ma.get('ma_50') else 'N/A'}")
        
        # 交叉信号
        signals = status.get('cross_signals', {})
        print(f"\n  【交叉信号】")
        for key, value in signals.items():
            if value:
                signal_text = '金叉' if value == 'golden_cross' else ('死叉' if value == 'death_cross' else value)
                print(f"    {key}: {signal_text}")
        
        # 最近交叉日期
        gc_ma = status.get('latest_golden_cross_ma_5_10')
        dc_ma = status.get('latest_death_cross_ma_5_10')
        gc_macd = status.get('latest_golden_cross_macd')
        dc_macd = status.get('latest_death_cross_macd')
        
        print(f"\n  【最近交叉】")
        if gc_ma:
            print(f"    MA5-10 金叉: {gc_ma[0]} ({gc_ma[1]}天前)")
        if dc_ma:
            print(f"    MA5-10 死叉: {dc_ma[0]} ({dc_ma[1]}天前)")
        if gc_macd:
            print(f"    MACD 金叉:   {gc_macd[0]} ({gc_macd[1]}天前)")
        if dc_macd:
            print(f"    MACD 死叉:   {dc_macd[0]} ({dc_macd[1]}天前)")
        
        # 百分位
        percentiles = status.get('percentile_ranks', {})
        print(f"\n  【历史百分位】")
        for key, value in percentiles.items():
            if value is not None:
                level = self.percentile_calculator.get_percentile_level(value)
                print(f"    {key}: {value:.1f}% ({level})")
        
        # MACD
        macd = status.get('macd', {})
        print(f"\n  【MACD】")
        print(f"    MACD:   {macd.get('macd', 0):.4f if macd.get('macd') else 'N/A'}")
        print(f"    信号线: {macd.get('macd_signal_line', 0):.4f if macd.get('macd_signal_line') else 'N/A'}")
        hist = macd.get('macd_histogram')
        if hist is not None:
            color = '红柱' if hist > 0 else '绿柱'
            print(f"    柱状图: {hist:.4f} ({color})")
        
        # RSI/KDJ
        tech = status.get('technical', {})
        print(f"\n  【技术指标】")
        rsi = tech.get('rsi')
        if rsi is not None:
            rsi_status = '超买' if rsi > 70 else ('超卖' if rsi < 30 else '中性')
            print(f"    RSI:  {rsi:.2f} ({rsi_status})")
        
        kdj_k = tech.get('kdj_k')
        if kdj_k is not None:
            kdj_status = '超买' if kdj_k > 80 else ('超卖' if kdj_k < 20 else '中性')
            print(f"    KDJ_K: {kdj_k:.2f} ({kdj_status})")
        
        print(f"{'='*60}\n")
    
    def generate_charts(self, save_dir: Optional[str] = None, show: bool = False):
        """
        生成所有分析图表
        
        Args:
            save_dir: 保存目录，默认为 constant.DEFAULT_FILE_PATH
            show: 是否显示图表
        """
        from plot.multi_chart_generator import IndexChartGenerator
        
        if self._chart_generator is None:
            self._chart_generator = IndexChartGenerator()
        
        if save_dir is None:
            save_dir = constant.DEFAULT_FILE_PATH
        
        self._chart_generator.generate_all_charts(
            self.data, 
            self.ts_code, 
            self.name,
            save_dir=save_dir,
            show=show
        )
    
    def get_data(self) -> pd.DataFrame:
        """
        获取分析后的数据
        
        Returns:
            pd.DataFrame: 包含分析结果的DataFrame
        """
        return self.data.copy()


def analyze_all_indices(save_charts: bool = True, print_status: bool = True):
    """
    分析所有指数
    
    Args:
        save_charts: 是否保存图表
        print_status: 是否打印状态摘要
    """
    ts_codes = list(constant.TS_CODE_NAME_DICT.keys())
    
    for ts_code in ts_codes:
        try:
            print(f"\n开始分析 {constant.TS_CODE_NAME_DICT.get(ts_code, ts_code)}...")
            analyzer = IndexAnalyzer(ts_code)
            analyzer.analyze()
            
            if print_status:
                analyzer.print_current_status()
            
            if save_charts:
                analyzer.generate_charts()
                
        except Exception as e:
            print(f"分析 {ts_code} 时出错: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    # 示例：分析上证指数
    analyzer = IndexAnalyzer('000001.SH')
    analyzer.analyze()
    analyzer.print_current_status()
