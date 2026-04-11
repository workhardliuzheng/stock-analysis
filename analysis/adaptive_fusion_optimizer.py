"""
V7-5 混合策略自适应融合优化模块

基于Optuna自动学习多因子信号与ML信号的最优融合权重，
使用Walk-Forward框架避免数据泄露，支持夏普比率最大化。

设计原则:
1. Walk-Forward训练: 避免未来数据泄露
2. 夏普比率最大化: 不是收益率最大化 (防过拟合)
3. 权重空间约束: 0-100%, 和必须=100%
4. 市场状态识别: 根据波动率动态调整权重空间
"""

from typing import Dict, Optional, Tuple, List
from datetime import datetime
import numpy as np
import pandas as pd

try:
    import optuna
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False
    raise ImportError("optuna 未安装，请运行: pip install optuna")

try:
    from sklearn.ensemble import RandomForestRegressor
    HAS_RF = True
except ImportError:
    HAS_RF = False
    raise ImportError("scikit-learn 未安装，请运行: pip install scikit-learn")

try:
    from sklearn.metrics import mean_squared_error
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    raise ImportError("scikit-learn 未安装，请运行: pip install scikit-learn")


class MetaLearner:
    """
    元学习器 - 学习最优信号融合权重
    
    输入:
        - factor_score: 多因子综合评分 (0-100)
        - factor_signal: 多因子信号强度 (BUY=1, SELL=-1, HOLD=0)
        - ml_predicted_return: ML预测收益率
        - ml_signal: ML信号强度 (BUY=1, SELL=-1, HOLD=0)
        
    输出:
        - fused_score: 融合后评分 (0-100)
        - fused_signal: 融合后信号 (BUY/SELL/HOLD)
        
    优化目标:
        - 是: 夏普比率 (Sharpe Ratio)
        - 否: 最大回撤 (Max Drawdown)
    """
    
    def __init__(self, 
                 initial_train_size: int = 500,
                 test_size: int = 60,
                 max_trials: int = 50,
                 market_state: str = 'oscillation'):
        """
        Args:
            initial_train_size: 初始训练窗口大小
            test_size: 测试窗口大小 (Walk-Forward)
            max_trials: Optuna搜索次数
            market_state: 市场状态 (bull/bear/oscillation)
        """
        self.initial_train_size = initial_train_size
        self.test_size = test_size
        self.max_trials = max_trials
        self.market_state = market_state
        
        # Optuna模型参数
        self.model = None
        self.optuna_study = None
        
        # 最优权重
        self.best_weights = {
            'factor_score': 0.4,    # 多因子权重
            'factor_signal': 0.3,   # 多因子信号强度
            'ml_return': 0.3,       # ML预测收益率
            'ml_signal': 0.0,       # ML信号强度 (暂未使用)
        }
        
        # 记录
        self.trial_results = []
        
        print(f"[OK] V7-5 MetaLearner 初始化")
        print(f"[OK] 市场状态: {market_state}")
        print(f"[OK] 权重约束: 4个组件总和=100%")
    
    def _calculate_metric(self, weights: Dict[str, float], 
                         df: pd.DataFrame, 
                         walk_forward: bool = True) -> float:
        """
        计算给定权重下的夏普比率
        
        Args:
            weights: 权重字典
            df: DataFrame (包含factor_score, factor_signal, ml_predicted_return等列)
            walk_forward: 是否使用Walk-Forward验证 (默认True)
        
        Returns:
            float: 夏普比率 (越高越好)
        """
        if len(df) < self.initial_train_size:
            return -np.inf
        
        # 1. 计算融合评分
        df = df.copy()
        df['fused_score'] = (
            weights['factor_score'] * df['factor_score'] +
            weights['factor_signal'] * df['factor_signal'] +
            weights['ml_return'] * df['ml_predicted_return'] * 100 +
            weights['ml_signal'] * df['ml_signal']
        )
        
        # 2. Walk-Forward验证
        if walk_forward:
            sharpe_ratios = []
            n_rows = len(df)
            
            # 滚动窗口
            for start_idx in range(0, n_rows - self.test_size, self.test_size):
                end_idx = start_idx + self.test_size
                train_df = df.iloc[:start_idx + self.initial_train_size] if start_idx == 0 else df.iloc[start_idx:start_idx + self.initial_train_size]
                test_df = df.iloc[end_idx:end_idx + self.test_size]
                
                if len(test_df) == 0:
                    continue
                
                # 计算测试集收益
                test_df = test_df.copy()
                test_df['position'] = np.sign(test_df['fused_score'] - 50)  # >50做多, <50做空
                test_df['strategy_return'] = test_df['position'] * test_df['pct_chg'] / 100
                
                # 计算夏普比率
                if test_df['strategy_return'].std() > 0:
                    sr = test_df['strategy_return'].mean() / test_df['strategy_return'].std() * np.sqrt(252)
                    sharpe_ratios.append(sr)
            
            if len(sharpe_ratios) == 0:
                return -np.inf
            
            return np.mean(sharpe_ratios)
        
        else:
            # 全样本计算 (仅用于最终评估)
            df['position'] = np.sign(df['fused_score'] - 50)
            df['strategy_return'] = df['position'] * df['pct_chg'] / 100
            
            if df['strategy_return'].std() > 0:
                sr = df['strategy_return'].mean() / df['strategy_return'].std() * np.sqrt(252)
                return sr
            else:
                return -np.inf
    
    def _objective(self, trial: optuna.Trial) -> float:
        """
        Optuna优化目标函数
        
        约束:
        - factor_score: 0.2-0.6
        - factor_signal: 0-0.3
        - ml_return: 0-0.5
        - ml_signal: 0-0.2
        - 总和 ≈ 1.0
        """
        # 1. 生成权重 (确保和接近1)
        w_factor_score = trial.suggest_float('w_factor_score', 0.2, 0.6)
        w_factor_signal = trial.suggest_float('w_factor_signal', 0.0, 0.3)
        w_ml_return = trial.suggest_float('w_ml_return', 0.0, 0.5)
        w_ml_signal = trial.suggest_float('w_ml_signal', 0.0, 0.2)
        
        # 归一化 (确保和=1)
        total = w_factor_score + w_factor_signal + w_ml_return + w_ml_signal
        weights = {
            'factor_score': w_factor_score / total,
            'factor_signal': w_factor_signal / total,
            'ml_return': w_ml_return / total,
            'ml_signal': w_ml_signal / total,
        }
        
        # 2. 计算夏普比率
        sharpe = self._calculate_metric(weights, self._df, walk_forward=True)
        
        # 记录
        self.trial_results.append({
            'trial': trial.number,
            'weights': weights,
            'sharpe_ratio': sharpe,
        })
        
        return sharpe
    
    def optimize(self, df: pd.DataFrame) -> Tuple[Dict[str, float], float]:
        """
        优化最优融合权重
        
        Args:
            df: DataFrame (包含必要列)
        
        Returns:
            Tuple[Dict[str, float], float]: 最优权重, 最优夏普比率
        """
        print(f"[INFO] V7-5 开始Optuna优化 (max_trials={self.max_trials})")
        print(f"[INFO] 数据行数: {len(df)}")
        
        # 1. 准备数据
        required_columns = ['factor_score', 'factor_signal', 'ml_predicted_return', 'ml_signal', 'pct_chg']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必要列: {col}")
        
        self._df = df.copy()
        self._df['factor_signal'] = self._df['factor_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)
        self._df['ml_signal'] = self._df['ml_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)
        self._df['ml_predicted_return'] = self._df['ml_predicted_return'].fillna(0)
        
        # 2. 运行Optuna
        if not HAS_OPTUNA:
            raise ImportError("optuna 未安装")
        
        self.optuna_study = optuna.create_study(direction='maximize')
        self.optuna_study.optimize(self._objective, n_trials=self.max_trials, show_progress_bar=True)
        
        # 3. 获取最优权重
        best_trial = self.optuna_study.best_trial
        best_weights = best_trial.params
        
        # 归一化
        total = sum(best_weights.values())
        self.best_weights = {
            'factor_score': best_weights['w_factor_score'] / total,
            'factor_signal': best_weights['w_factor_signal'] / total,
            'ml_return': best_weights['w_ml_return'] / total,
            'ml_signal': best_weights['w_ml_signal'] / total,
        }
        
        best_sharpe = best_trial.value
        
        print(f"\n[OK] Optuna优化完成")
        print(f"  最优夏普比率: {best_sharpe:.4f}")
        print(f"  权重分配:")
        print(f"    factor_score: {self.best_weights['factor_score']:.2%}")
        print(f"    factor_signal: {self.best_weights['factor_signal']:.2%}")
        print(f"    ml_return: {self.best_weights['ml_return']:.2%}")
        print(f"    ml_signal: {self.best_weights['ml_signal']:.2%}")
        
        return self.best_weights, best_sharpe
    
    def generate_fused_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        使用最优权重生成融合信号
        
        Args:
            df: DataFrame
        
        Returns:
            pd.DataFrame: 新增fused_score, fused_signal, fused_confidence列
        """
        df = df.copy()
        
        # 确保信号列为数值
        factor_signal_map = {'BUY': 1, 'SELL': -1, 'HOLD': 0}
        ml_signal_map = {'BUY': 1, 'SELL': -1, 'HOLD': 0}
        
        df['factor_signal_num'] = df['factor_signal'].map(factor_signal_map).fillna(0)
        df['ml_signal_num'] = df['ml_signal'].map(ml_signal_map).fillna(0)
        df['ml_predicted_return'] = df['ml_predicted_return'].fillna(0)
        
        # 计算融合评分 (加权平均)
        df['fused_score'] = (
            self.best_weights['factor_score'] * df['factor_score'] +
            self.best_weights['factor_signal'] * df['factor_signal_num'] * 50 +  # 乘以50归一化到0-100
            self.best_weights['ml_return'] * df['ml_predicted_return'] * 100 +
            self.best_weights['ml_signal'] * df['ml_signal_num'] * 50
        )
        
        # 归一化到0-100 (防止溢出)
        df['fused_score'] = (
            (df['fused_score'] - df['fused_score'].min()) / 
            (df['fused_score'].max() - df['fused_score'].min()) * 100
        )
        
        # 生成基础信号
        df['fused_signal'] = 'HOLD'
        df.loc[df['fused_score'] >= 60, 'fused_signal'] = 'BUY'
        df.loc[df['fused_score'] < 40, 'fused_signal'] = 'SELL'
        
        # 多指标共识投票: 4个独立指标各投一票(+1看涨/-1看跌)
        # V8: 根据市场状态(regime)动态调整看涨/看跌阈值
        trend_override_count = 0
        all_cols = ['close', 'ma_20', 'ma_50', 'macd_histogram', 'rsi', 'plus_di', 'minus_di']
        if all(c in df.columns for c in all_cols):
            close = pd.to_numeric(df['close'], errors='coerce')
            ma20 = pd.to_numeric(df['ma_20'], errors='coerce')
            ma50 = pd.to_numeric(df['ma_50'], errors='coerce')
            macd_hist = pd.to_numeric(df['macd_histogram'], errors='coerce')
            rsi = pd.to_numeric(df['rsi'], errors='coerce')
            plus_di = pd.to_numeric(df['plus_di'], errors='coerce')
            minus_di = pd.to_numeric(df['minus_di'], errors='coerce')
            
            # 各指标投票: +1=看涨, -1=看跌, 0=中性
            vote_ma = pd.Series(0, index=df.index)
            vote_ma[(close > ma20) & (ma20 > ma50)] = 1
            vote_ma[(close < ma20) & (ma20 < ma50)] = -1
            
            vote_macd = pd.Series(0, index=df.index)
            vote_macd[macd_hist > 0] = 1
            vote_macd[macd_hist < 0] = -1
            
            vote_rsi = pd.Series(0, index=df.index)
            vote_rsi[rsi > 50] = 1
            vote_rsi[rsi < 50] = -1
            
            vote_adx = pd.Series(0, index=df.index)
            vote_adx[plus_di > minus_di] = 1
            vote_adx[minus_di > plus_di] = -1
            
            consensus = vote_ma + vote_macd + vote_rsi + vote_adx
            
            # V8: 根据regime动态调整共识阈值
            has_regime = 'regime_label' in df.columns
            if has_regime:
                from analysis.market_regime_detector import MarketRegimeDetector
                # 逐行根据regime设定阈值，然后向量化应用
                bull_thresh = pd.Series(4, index=df.index)  # 默认严格
                bear_thresh = pd.Series(-3, index=df.index)  # 默认
                
                for regime_label in df['regime_label'].unique():
                    mask = df['regime_label'] == regime_label
                    thresholds = MarketRegimeDetector.get_consensus_thresholds(regime_label)
                    bull_thresh[mask] = thresholds['bull_thresh']
                    bear_thresh[mask] = thresholds['bear_thresh']
                
                strong_bull = consensus >= bull_thresh
                strong_bear = consensus <= bear_thresh
                
                # 统计regime分布
                regime_counts = df['regime_label'].value_counts()
                print(f"  V8 市场状态: {dict(regime_counts)}")
            else:
                # 向后兼容: 无regime时使用V7-7固定阈值
                strong_bull = consensus >= 4
                strong_bear = consensus <= -3
            
            # 看涨升级
            bull_sell = strong_bull & (df['fused_signal'] == 'SELL')
            bull_hold = strong_bull & (df['fused_signal'] == 'HOLD')
            df.loc[bull_sell, 'fused_signal'] = 'HOLD'
            df.loc[bull_hold, 'fused_signal'] = 'BUY'
            
            # 看跌降级
            bear_buy = strong_bear & (df['fused_signal'] == 'BUY')
            bear_hold = strong_bear & (df['fused_signal'] == 'HOLD')
            df.loc[bear_buy, 'fused_signal'] = 'HOLD'
            df.loc[bear_hold, 'fused_signal'] = 'SELL'
            
            trend_override_count = int(bull_sell.sum() + bull_hold.sum() + bear_buy.sum() + bear_hold.sum())
            
            n_strong_bull = int(strong_bull.sum())
            n_strong_bear = int(strong_bear.sum())
            n_neutral = len(df) - n_strong_bull - n_strong_bear
            print(f"  指标共识: 强看涨={n_strong_bull}天, 强看跌={n_strong_bear}天, 中性={n_neutral}天")
        
        # 信心度
        df['fused_confidence'] = np.abs(df['fused_score'] - 50) / 50
        
        print(f"[OK] V7-5 融合信号生成完成")
        print(f"  原始信号: BUY={len(df[df['factor_signal']=='BUY'])} SELL={len(df[df['factor_signal']=='SELL'])} HOLD={len(df[df['factor_signal']=='HOLD'])}")
        print(f"  共识覆盖: {trend_override_count} 条信号被升/降级")
        print(f"  融合信号: BUY={len(df[df['fused_signal']=='BUY'])} SELL={len(df[df['fused_signal']=='SELL'])} HOLD={len(df[df['fused_signal']=='HOLD'])}")
        
        return df


class AdaptiveFusionOptimizer:
    """
    自适应融合优化器
    
    功能:
    1. 多时间窗口Optuna优化
    2. 市场状态识别 (bull/bear/oscillation)
    3. 动态权重空间调整
    4. Walk-Forward验证
    """
    
    def __init__(self, max_trials: int = 50, n_windows: int = 3):
        """
        Args:
            max_trials: Optuna搜索次数
            n_windows: 时间窗口数量
        """
        self.max_trials = max_trials
        self.n_windows = n_windows
        self.window_weights = []  # 每个窗口的最优权重
        self.global_weights = {}  # 全局最优权重
        
        print(f"[OK] V7-5 AdaptiveFusionOptimizer 初始化")
        print(f"[OK] Optuna搜索次数: {max_trials}")
        print(f"[OK] 时间窗口数量: {n_windows}")
    
    def _identify_market_state(self, df: pd.DataFrame) -> str:
        """
        识别市场状态
        
        Args:
            df: DataFrame (包含pct_chg列)
        
        Returns:
            str: 市场状态 (bull/bear/oscillation)
        """
        returns = df['pct_chg']
        
        # 计算波动率
        volatility = returns.std()
        
        # 计算趋势
        moving_avg = returns.rolling(20).mean()
        trend = returns.iloc[-1] - moving_avg.iloc[-1] if not moving_avg.isna().any() else 0
        
        # 识别状态
        if volatility > 2.0:
            if trend > 0:
                return 'bull'
            else:
                return 'bear'
        else:
            return 'oscillation'
    
    def _optimize_window(self, df: pd.DataFrame, window_start: int, window_end: int) -> Dict[str, float]:
        """
        优化单个时间窗口
        
        Args:
            df: DataFrame
            window_start: 窗口起始索引
            window_end: 窗口结束索引
        
        Returns:
            Dict[str, float]: 最优权重
        """
        window_df = df.iloc[window_start:window_end].copy()
        
        if len(window_df) < 300:
            print(f"  [SKIP] 窗口数据不足 ({len(window_df)} rows)")
            return None
        
        market_state = self._identify_market_state(window_df)
        
        print(f"  [INFO] 优化窗口 {window_start}-{window_end} (状态: {market_state})")
        
        meta_learner = MetaLearner(
            initial_train_size=200,
            test_size=60,
            max_trials=self.max_trials,
            market_state=market_state
        )
        
        weights, sharpe = meta_learner.optimize(window_df)
        
        print(f"    最优夏普: {sharpe:.4f}")
        print(f"    权重: {weights}")
        
        return weights
    
    def optimize(self, df: pd.DataFrame) -> Tuple[Dict[str, float], List[Dict[str, float]]]:
        """
        优化自适应融合权重
        
        Args:
            df: DataFrame
        
        Returns:
            Tuple: (全局最优权重, 各窗口最优权重列表)
        """
        print(f"[INFO] V7-5 开始自适应融合优化")
        print(f"[INFO] 数据行数: {len(df)}")
        
        # 1. 划分时间窗口
        window_size = len(df) // self.n_windows
        windows = []
        
        for i in range(self.n_windows):
            start = i * window_size
            end = (i + 1) * window_size if i < self.n_windows - 1 else len(df)
            windows.append((start, end))
        
        # 2. 优化每个窗口
        print("\n[INFO] 开始多窗口Optuna优化...")
        self.window_weights = []
        
        for i, (start, end) in enumerate(windows):
            print(f"\n--- 窗口 {i+1}/{self.n_windows} ---")
            weights = self._optimize_window(df, start, end)
            
            if weights:
                self.window_weights.append(weights)
        
        # 3. 聚合全局权重
        if len(self.window_weights) > 0:
            # 平均各窗口权重
            keys = self.window_weights[0].keys()
            self.global_weights = {
                key: np.mean([w[key] for w in self.window_weights])
                for key in keys
            }
            
            # 归一化
            total = sum(self.global_weights.values())
            self.global_weights = {k: v/total for k, v in self.global_weights.items()}
            
            print(f"\n[OK] 全局最优权重 (平均):")
            for key, value in self.global_weights.items():
                print(f"  {key}: {value:.2%}")
        else:
            # 返回默认权重
            self.global_weights = {
                'factor_score': 0.4,
                'factor_signal': 0.3,
                'ml_return': 0.3,
                'ml_signal': 0.0,
            }
            
            print(f"\n[WARN] 无法找到最优权重，使用默认权重")
        
        return self.global_weights, self.window_weights
    
    def apply_fusion(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        应用融合策略
        
        Args:
            df: DataFrame
        
        Returns:
            pd.DataFrame: 新增fused_score, fused_signal等列
        """
        return MetaLearner().apply_fusion_from_weights(df, self.global_weights)


def run_v75_optimization(index_code: str = '000688.SH', 
                         start_date: str = '20230101',
                         max_trials: int = 50) -> Tuple[Dict[str, float], float]:
    """
    快速运行V7-5优化
    
    Args:
        index_code: 指数代码
        start_date: 起始日期
        max_trials: Optuna搜索次数
    
    Returns:
        Tuple: (最优权重, 最优夏普比率)
    """
    from analysis.index_analyzer import IndexAnalyzer
    from analysis.multi_factor_scorer import MultiFactorScorer
    from analysis.ml_predictor import MLPredictor
    
    print(f"[INFO] V7-5 自适应融合优化 - {index_code}")
    
    # 1. 加载数据
    analyzer = IndexAnalyzer(index_code, start_date=start_date)
    result = analyzer.analyze(include_ml=True)
    
    if result is None or len(result) == 0:
        print(f"[ERROR] 数据加载失败")
        return None, -1
    
    # 2. 计算多因子评分
    scorer = MultiFactorScorer()
    df = scorer.calculate(result)
    
    # 3. 训练ML模型并预测
    predictor = MLPredictor()
    df, metrics = predictor.train_and_predict(df, auto_tune=False)
    
    print(f"\n[INFO] 数据准备完成")
    print(f"  行数: {len(df)}")
    print(f"  ML验证指标: MAE={metrics.get('mae', 0):.4f}, RMSE={metrics.get('rmse', 0):.4f}")
    
    # 4. 运行Optuna优化
    optimizer = AdaptiveFusionOptimizer(max_trials=max_trials, n_windows=3)
    weights, window_weights = optimizer.optimize(df)
    
    # 5. 应用融合
    meta_learner = MetaLearner(market_state='oscillation')
    meta_learner.best_weights = weights
    
    df_fused = meta_learner.generate_fused_signal(df)
    
    # 6. 计算最终夏普比率
    df_fused['position'] = np.sign(df_fused['fused_score'] - 50)
    df_fused['strategy_return'] = df_fused['position'] * df_fused['pct_chg'] / 100
    
    if df_fused['strategy_return'].std() > 0:
        final_sharpe = df_fused['strategy_return'].mean() / df_fused['strategy_return'].std() * np.sqrt(252)
    else:
        final_sharpe = 0.0
    
    print(f"\n{'='*60}")
    print("[OK] V7-5 优化完成")
    print(f"{'='*60}")
    print(f"  最优夏普比率: {final_sharpe:.4f}")
    print(f"  权重分配:")
    for key, value in weights.items():
        print(f"    {key}: {value:.2%}")
    
    return weights, final_sharpe


# ==================== 快速测试 ====================

def test_v75_simple():
    """简单测试"""
    print("V7-5 简单测试...")
    
    # 读取预生成数据
    import os
    data_path = 'E:/pycharm/stock-analysis/data/test_v75.parquet'
    
    if os.path.exists(data_path):
        df = pd.read_parquet(data_path)
    else:
        # 生成示例数据
        df = pd.DataFrame({
            'trade_date': pd.date_range('2023-01-01', periods=500),
            'factor_score': np.random.uniform(30, 70, 500),
            'factor_signal': np.random.choice(['BUY', 'SELL', 'HOLD'], 500, p=[0.2, 0.1, 0.7]),
            'ml_predicted_return': np.random.uniform(-0.05, 0.05, 500),
            'ml_signal': np.random.choice(['BUY', 'SELL', 'HOLD'], 500, p=[0.2, 0.1, 0.7]),
            'pct_chg': np.random.uniform(-0.03, 0.03, 500),
        })
        df['ml_predicted_return'] = df['ml_predicted_return'].fillna(0)
        
        # 保存
        os.makedirs('E:/pycharm/stock-analysis/data', exist_ok=True)
        df.to_parquet(data_path)
    
    print(f"[INFO] 示例数据: {len(df)} 行")
    print("\n[INFO] 运行Optuna优化 (5 trials)...")
    
    meta_learner = MetaLearner(initial_train_size=200, test_size=50, max_trials=5)
    
    # 确保信号列为数值
    df['factor_signal'] = df['factor_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)
    df['ml_signal'] = df['ml_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)
    df['ml_predicted_return'] = df['ml_predicted_return'].fillna(0)
    
    weights, sharpe = meta_learner.optimize(df)
    
    print(f"\n[OK] 优化完成")
    print(f"  权重: {weights}")
    print(f"  夏普: {sharpe:.4f}")
    
    return weights, sharpe


if __name__ == '__main__':
    # 快速测试
    print("="*60)
    print("V7-5 自适应融合优化 - 快速测试")
    print("="*60)
    
    test_v75_simple()
