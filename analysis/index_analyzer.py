"""
指数技术分析器（重构版）

整合交叉信号检测、历史百分位计算、多因子评分、ML预测、信号生成、回测
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
from analysis.multi_factor_scorer import MultiFactorScorer
from analysis.signal_generator import SignalGenerator
from analysis.backtester import Backtester
from analysis.position_manager import PositionManager, PositionConfig
from util.class_util import ClassUtil
from util.date_util import TimeUtils


class IndexAnalyzer:
    """
    指数技术分析器（重构版）
    
    功能：
    1. 计算交叉信号（均线金叉死叉、MACD金叉死叉）
    2. 计算历史百分位（偏离率、成交量、MACD等）
    3. 多因子综合评分（趋势/动量/成交量/估值/波动率）
    4. 机器学习预测（XGBoost，可选）
    5. 信号整合与回测
    6. 生成多维度分析图表
    7. 提供当前市场状态摘要
    
    使用示例:
        analyzer = IndexAnalyzer('000001.SH')
        df = analyzer.analyze()
        signal = analyzer.get_current_signal()
        results = analyzer.backtest()
        analyzer.generate_charts(save_path='output/')
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
        self.multi_factor_scorer = MultiFactorScorer()
        self.signal_generator = SignalGenerator()
        self._ml_predictor = None  # 延迟加载，避免强制依赖 xgboost
        
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
    
    def analyze(self, include_ml: bool = True, auto_tune: bool = False,
                feature_selection: bool = False, max_features: int = 20) -> pd.DataFrame:
        """
        执行完整分析流程
        
        计算交叉信号、历史百分位、多因子评分，可选ML预测，最终生成信号
        
        Args:
            include_ml: 是否包含 ML 预测 (需要 xgboost/sklearn)
            auto_tune: 是否使用 Optuna 自动调优 ML 超参数
            feature_selection: 是否进行特征重要性筛选
            max_features: 保留的最大特征数量
        
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
        
        # 多因子评分
        print(f"正在计算 {self.name} 的多因子评分...")
        self.data = self.multi_factor_scorer.calculate(self.data)
        
        # ML 预测（使用滚动预测避免数据泄露）
        if include_ml:
            try:
                predictor = self._get_ml_predictor(feature_selection=feature_selection, max_features=max_features)
                print(f"正在滚动预测 {self.name}（回归模式，避免数据泄露）...")
                self.data, metrics = predictor.train_and_predict(self.data, auto_tune=auto_tune)
                print(f"  ML验证指标: {metrics}")
            except ImportError as e:
                print(f"  ML模块不可用({e})，跳过ML预测")
                self.data['ml_predicted_return'] = 0.0
                self.data['ml_probability'] = 0.5
                self.data['ml_probability_raw'] = 0.5
                self.data['ml_signal'] = 'HOLD'
            except Exception as e:
                print(f"  ML预测失败: {e}，使用默认值")
                self.data['ml_predicted_return'] = 0.0
                self.data['ml_probability'] = 0.5
                self.data['ml_probability_raw'] = 0.5
                self.data['ml_signal'] = 'HOLD'
        else:
            self.data['ml_predicted_return'] = 0.0
            self.data['ml_probability'] = 0.5
            self.data['ml_probability_raw'] = 0.5
            self.data['ml_signal'] = 'HOLD'
        
        # 信号整合
        print(f"正在生成 {self.name} 的最终信号...")
        self.data = self.signal_generator.generate(self.data)
        
        return self.data
    
    def _get_ml_predictor(self, feature_selection: bool = False, max_features: int = 20):
        """延迟加载 ML 预测器"""
        if self._ml_predictor is None:
            from analysis.ml_predictor import MLPredictor
            self._ml_predictor = MLPredictor(
                feature_selection=feature_selection,
                max_features=max_features
            )
        return self._ml_predictor
    
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
    
    def get_current_signal(self) -> Dict:
        """
        获取当日交易信号
        
        Returns:
            Dict: 包含信号详情的字典
        """
        if len(self.data) == 0 or 'final_signal' not in self.data.columns:
            return {}
        
        latest = self.data.iloc[-1]
        
        signal_info = {
            'ts_code': self.ts_code,
            'name': self.name,
            'trade_date': str(latest.get('trade_date', '')),
            'close': latest.get('close'),
            'pct_chg': latest.get('pct_chg'),
            'final_signal': latest.get('final_signal', 'HOLD'),
            'final_confidence': latest.get('final_confidence', 0.5),
            'factor_score': latest.get('factor_score', 50),
            'factor_signal': latest.get('factor_signal', 'HOLD'),
            'trend_state': latest.get('trend_state', 'sideways'),
            'ml_predicted_return': latest.get('ml_predicted_return', 0.0),
            'ml_probability': latest.get('ml_probability', 0.5),
            'ml_signal': latest.get('ml_signal', 'HOLD'),
        }
        
        # 解析因子明细
        factor_detail = latest.get('factor_detail')
        if factor_detail and isinstance(factor_detail, str):
            import json
            try:
                signal_info['factor_detail'] = json.loads(factor_detail)
            except (json.JSONDecodeError, TypeError):
                pass
        
        return signal_info
    
    def print_current_signal(self):
        """打印当日交易信号"""
        sig = self.get_current_signal()
        if not sig:
            print(f"{self.ts_code} 无信号数据，请先运行 analyze()")
            return
        
        signal_text = sig['final_signal']
        signal_icon = {'BUY': '[买入]', 'SELL': '[卖出]', 'HOLD': '[持有]'}
        
        print(f"\n{'=' * 60}")
        print(f"  {sig['name']} ({sig['ts_code']}) 交易信号")
        print(f"{'=' * 60}")
        print(f"  日期: {sig['trade_date']}  收盘: {sig.get('close', 0):.2f}  涨跌: {sig.get('pct_chg', 0):.2f}%")
        print(f"\n  >>> 最终信号: {signal_icon.get(signal_text, signal_text)} "
              f"置信度: {sig.get('final_confidence', 0):.1%}")
        print(f"  趋势状态: {sig.get('trend_state', 'N/A')}")
        print(f"\n  多因子评分: {sig.get('factor_score', 0):.1f}/100 → {sig.get('factor_signal', 'N/A')}")
        ml_ret = sig.get('ml_predicted_return', 0)
        if ml_ret is not None and not (isinstance(ml_ret, float) and np.isnan(ml_ret)):
            ml_ret_display = f"{ml_ret:+.3f}%"
        else:
            ml_ret_display = "N/A"
        print(f"  ML预测收益: {ml_ret_display}  伪概率: {sig.get('ml_probability', 0):.1%} → {sig.get('ml_signal', 'N/A')}")
        
        detail = sig.get('factor_detail', {})
        if detail:
            print(f"\n  因子明细:")
            for k, v in detail.items():
                print(f"    {k}: {v:.1f}")
        
        print(f"{'=' * 60}\n")
    
    def backtest(self, strategy: str = 'all') -> dict:
        """
        运行回测
        
        Args:
            strategy: 'factor' / 'ml' / 'combined' / 'all'
        
        Returns:
            dict: 回测结果
        """
        if 'final_signal' not in self.data.columns:
            print("请先运行 analyze() 生成信号")
            return {}
        
        bt = Backtester()
        
        if strategy == 'all':
            strategies = {}
            if 'factor_signal' in self.data.columns:
                strategies['多因子策略'] = 'factor_signal'
            if 'ml_signal' in self.data.columns:
                strategies['ML策略'] = 'ml_signal'
            if 'final_signal' in self.data.columns:
                strategies['混合策略'] = 'final_signal'
            
            results = bt.compare_strategies(self.data, strategies)
            bt.print_comparison(results, index_name=f"{self.name} ({self.ts_code})")
            return results
        else:
            col_map = {
                'factor': 'factor_signal',
                'ml': 'ml_signal',
                'combined': 'final_signal',
            }
            col = col_map.get(strategy, 'final_signal')
            if col not in self.data.columns:
                print(f"信号列 {col} 不存在")
                return {}
            
            result = bt.run(self.data, col)
            bt.print_report(result, index_name=f"{self.name} ({self.ts_code})")
            return result
    
    def get_data(self) -> pd.DataFrame:
        """
        获取分析后的数据
        
        Returns:
            pd.DataFrame: 包含分析结果的DataFrame
        """
        return self.data.copy()


def analyze_all_indices(save_charts: bool = True, print_status: bool = True,
                        include_ml: bool = True):
    """
    分析所有指数
    
    Args:
        save_charts: 是否保存图表
        print_status: 是否打印状态摘要
        include_ml: 是否包含 ML 预测
    """
    ts_codes = list(constant.TS_CODE_NAME_DICT.keys())
    
    for ts_code in ts_codes:
        try:
            print(f"\n开始分析 {constant.TS_CODE_NAME_DICT.get(ts_code, ts_code)}...")
            analyzer = IndexAnalyzer(ts_code)
            analyzer.analyze(include_ml=include_ml)
            
            if print_status:
                analyzer.print_current_signal()
            
            if save_charts:
                analyzer.generate_charts()
                
        except Exception as e:
            print(f"分析 {ts_code} 时出错: {e}")
            import traceback
            traceback.print_exc()


def signal_all_indices(ts_code: Optional[str] = None, include_ml: bool = True,
                       auto_tune: bool = False, feature_selection: bool = False,
                       max_features: int = 20, **kwargs):
    """
    生成指数交易信号
    
    Args:
        ts_code: 指定指数代码，None 表示全部
        include_ml: 是否包含 ML 预测
        auto_tune: 是否使用 Optuna 自动调优
        feature_selection: 是否进行特征重要性筛选
        max_features: 保留的最大特征数量
        **kwargs: 兼容 main.py 传入的其他参数 (model_type 等)
    """
    if ts_code:
        codes = [ts_code]
    else:
        codes = list(constant.TS_CODE_NAME_DICT.keys())
    
    for code in codes:
        try:
            analyzer = IndexAnalyzer(code)
            analyzer.analyze(
                include_ml=include_ml, 
                auto_tune=auto_tune,
                feature_selection=feature_selection,
                max_features=max_features
            )
            analyzer.print_current_signal()
        except Exception as e:
            print(f"生成 {code} 信号时出错: {e}")
            import traceback
            traceback.print_exc()


def backtest_all_indices(ts_code: Optional[List[str]] = None, strategy: str = 'all',
                         include_ml: bool = True, auto_tune: bool = False,
                         commission_rate: float = 0.00006,
                         execution_timing: str = 'close',
                         feature_selection: bool = False,
                         max_features: int = 20,
                         use_multi_index_backtest: bool = False,
                         **kwargs):
    """
    回测指数策略
    
    Args:
        ts_code: 指定指数代码列表，None 表示全部
        strategy: 策略类型 factor/ml/combined/all
        include_ml: 是否包含 ML 预测
        auto_tune: 是否使用 Optuna 自动调优
        commission_rate: 单边佣金率
        execution_timing: 执行时机 open/close
        feature_selection: 是否进行特征重要性筛选
        max_features: 保留的最大特征数量
        use_multi_index_backtest: 是否使用多指数组合回测（默认False，单指数独立回测）
        **kwargs: 兼容 main.py 传入的其他参数 (model_type 等)
    """
    if ts_code:
        codes = ts_code if isinstance(ts_code, list) else [ts_code]
    else:
        codes = list(constant.TS_CODE_NAME_DICT.keys())
    
    if use_multi_index_backtest:
        # 多指数组合回测
        backtest_multi_index(
            codes=codes,
            strategy=strategy,
            include_ml=include_ml,
            auto_tune=auto_tune,
            commission_rate=commission_rate,
            execution_timing=execution_timing,
            feature_selection=feature_selection,
            max_features=max_features
        )
    else:
        # 单指数独立回测（默认）
        for code in codes:
            try:
                name = constant.TS_CODE_NAME_DICT.get(code, code)
                print(f"\n{'#' * 60}")
                print(f"  回测 {name} ({code})")
                print(f"{'#' * 60}")
                
                analyzer = IndexAnalyzer(code)
                analyzer.analyze(
                    include_ml=include_ml, 
                    auto_tune=auto_tune,
                    feature_selection=feature_selection,
                    max_features=max_features
                )
                
                # 使用自定义回测参数
                bt = Backtester(
                    commission_rate=commission_rate,
                    execution_timing=execution_timing
                )
                
                if strategy == 'all':
                    strategies = {}
                    if 'factor_signal' in analyzer.data.columns:
                        strategies['多因子策略'] = 'factor_signal'
                    if 'ml_signal' in analyzer.data.columns:
                        strategies['ML策略'] = 'ml_signal'
                    if 'final_signal' in analyzer.data.columns:
                        strategies['混合策略'] = 'final_signal'
                    results = bt.compare_strategies(analyzer.data, strategies)
                    bt.print_comparison(results, index_name=f"{name} ({code})")
                else:
                    col_map = {
                        'factor': 'factor_signal',
                        'ml': 'ml_signal',
                        'combined': 'final_signal',
                    }
                    col = col_map.get(strategy, 'final_signal')
                    if col in analyzer.data.columns:
                        result = bt.run(analyzer.data, col)
                        bt.print_report(result, index_name=f"{name} ({code})")
                    else:
                        print(f"信号列 {col} 不存在")
            except Exception as e:
                print(f"回测 {code} 时出错: {e}")
                import traceback
                traceback.print_exc()


def backtest_multi_index(codes: List[str],
                        strategy: str = 'ml',
                        include_ml: bool = True,
                        auto_tune: bool = False,
                        commission_rate: float = 0.00006,
                        execution_timing: str = 'open',
                        feature_selection: bool = False,
                        max_features: int = 20,
                        initial_capital: float = 100000):
    """
    多指数组合回测
    
    Args:
        codes: 指数代码列表
        strategy: 策略类型 (ml/combined)
        include_ml: 是否包含 ML 预测
        auto_tune: 是否使用 Optuna
        commission_rate: 单边佣金率
        execution_timing: 执行时机
        feature_selection: 是否特征筛选
        max_features: 最大特征数
        initial_capital: 初始资金
    """
    from analysis.multi_index_backtester import MultiIndexBacktester
    from analysis.backtester import Backtester
    
    print(f"\n{'=' * 80}")
    print(f"  多指数组合回测")
    print(f"{'=' * 80}")
    print(f"  指数: {', '.join(codes)}")
    print(f"  策略: {strategy}")
    print(f"  初始资金: {initial_capital:,.0f} 元")
    print(f"{'=' * 80}\n")
    
    # 加载所有指数数据
    df_list = []
    code_list = []
    name_list = []
    
    for code in codes:
        try:
            name = constant.TS_CODE_NAME_DICT.get(code, code)
            analyzer = IndexAnalyzer(code)
            analyzer.analyze(include_ml=include_ml, auto_tune=auto_tune,
                           feature_selection=feature_selection,
                           max_features=max_features)
            
            # 确保有信号列
            if strategy == 'ml':
                signal_col = 'ml_signal'
            elif strategy == 'combined':
                signal_col = 'final_signal'
            else:
                signal_col = 'final_signal'
            
            if signal_col not in analyzer.data.columns:
                print(f"  {name}: 信号列 {signal_col} 不存在")
                continue
            
            df_list.append(analyzer.data)
            code_list.append(code)
            name_list.append(name)
            
            print(f"  {name} ({code}): {len(analyzer.data)} 条数据")
        except Exception as e:
            print(f"  加载 {code} 失败: {e}")
    
    if not df_list:
        print("  没有可用的指数数据")
        return
    
    # 运行多指数回测
    mib = MultiIndexBacktester(
        initial_capital=initial_capital,
        commission_rate=commission_rate,
        execution_timing=execution_timing
    )
    
    signal_columns = [signal_col] * len(df_list)
    
    try:
        result = mib.run(
            df_list=df_list,
            code_list=code_list,
            name_list=name_list,
            signal_columns=signal_columns
        )
        
        if 'error' in result:
            print(f"  回测失败: {result['error']}")
            return
        
        # 打印组合回测结果
        print(f"\n{'=' * 80}")
        print(f"  组合回测结果")
        print(f"{'=' * 80}")
        print(f"  总收益率:   {result['total_return']:>+7.1f}%")
        print(f"  年化收益:   {result['annualized_return']:>+7.1f}%")
        print(f"  最大回撤:   {result['max_drawdown']:>+7.1f}%")
        print(f"  夏普比率:   {result['sharpe_ratio']:>+6.2f}")
        print(f"  总交易日:   {result['total_days']} 天")
        print(f"{'=' * 80}\n")
        
        # 打印各指数回测结果对比
        print(f"  各指数回测结果对比:")
        print(f"{'=' * 80}")
        print(f"  {'指数':<15} {'总收益':>8} {'年化':>8} {'最大回撤':>8} {'夏普':>6}")
        print(f"{'-' * 80}")
        
        for code, index_result in result['index_results'].items():
            name = constant.TS_CODE_NAME_DICT.get(code, code)
            if 'error' not in index_result:
                tr = index_result.get('total_return', 0) * 100
                ar = index_result.get('annualized_return', 0) * 100
                md = index_result.get('max_drawdown', 0) * 100
                sr = index_result.get('sharpe_ratio', 0)
                print(f"  {name:<15} {tr:>+7.1f}% {ar:>+7.1f}% {md:>+7.1f}% {sr:>+6.2f}")
        
        print(f"{'=' * 80}\n")
        
        # 生成回测日志报告
        generate_backtest_report(result, codes)
        
    except Exception as e:
        print(f"  多指数回测失败: {e}")
        import traceback
        traceback.print_exc()


def generate_backtest_report(result: dict, codes: List[str]):
    """生成回测报告并写入 BACKTEST_LOG.md"""
    # 简单的回测报告
    import datetime
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    
    report = f"""
---
## 多指数组合回测 ({today})

**组合配置:**
- 指数: {', '.join(codes)}
- 策略: ML策略
- 初始资金: 100,000 元
- 佣金: 万0.6
- 执行时机: T+1开盘价

**组合回测结果:**
| 指标 | 数值 |
|------|------|
| 总收益率 | {result['total_return']:>+7.1f}% |
| 年化收益 | {result['annualized_return']:>+7.1f}% |
| 最大回撤 | {result['max_drawdown']:>+7.1f}% |
| 夏普比率 | {result['sharpe_ratio']:>+6.2f} |
| 总交易日 | {result['total_days']} 天 |

**各指数回测结果:**

| 指数 | 总收益 | 年化 | 最大回撤 | 夏普 |
|------|--------|------|---------|------|
"""
    
    for code, index_result in result['index_results'].items():
        name = constant.TS_CODE_NAME_DICT.get(code, code)
        if 'error' not in index_result:
            tr = index_result.get('total_return', 0) * 100
            ar = index_result.get('annualized_return', 0) * 100
            md = index_result.get('max_drawdown', 0) * 100
            sr = index_result.get('sharpe_ratio', 0)
            report += f"| {name} | {tr:>+7.1f}% | {ar:>+7.1f}% | {md:>+7.1f}% | {sr:>+6.2f} |\n"
    
    report += f"""\n**说明:**
- 组合采用动态仓位分配，基于各指数预测收益和风险
- 单指数最大仓位 30%，总仓位最大 90%
- 当所有指数预测为负时自动空仓
"""
    
    # 写入文件（简单追加）
    print("\n回测报告已生成（可手动添加到 BACKTEST_LOG.md）")


if __name__ == '__main__':
    # 示例：分析上证指数
    analyzer = IndexAnalyzer('000001.SH')
    analyzer.analyze()
    analyzer.print_current_status()
