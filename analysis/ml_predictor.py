"""
机器学习预测模块

使用 XGBoost 回归器，基于技术指标特征预测指数次日收益率（方案B：回归目标），
采用 Walk-Forward 验证避免未来数据泄露，支持 Optuna 超参数自动调优。

改进历史:
- v1: 二分类模型 (XGBClassifier)，标签为次日涨跌方向
- v2: 回归模型 (XGBRegressor)，标签为次日实际收益率
      + Optuna 超参数自动调优 (Walk-Forward 框架内)
"""

import json
import os
import pickle
from typing import Optional, Dict, List

import numpy as np
import pandas as pd

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

try:
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False


class MLPredictor:
    """
    XGBoost 机器学习预测器（回归版）

    特征工程: 从技术指标中提取 ~35 个特征
    标签: 次日实际收益率 (pct_chg / 100)
    验证: Walk-Forward 滚动验证
    调优: Optuna 超参数搜索（可选）

    使用示例:
        predictor = MLPredictor()
        # 滚动训练+预测 (新增 ml_predicted_return, ml_probability, ml_signal 列)
        df, metrics = predictor.train_and_predict(df)
        # 带超参数调优
        df, metrics = predictor.train_and_predict(df, auto_tune=True)
        # 保存/加载模型
        predictor.save_model('models/000300.pkl')
        predictor.load_model('models/000300.pkl')
    """

    DEFAULT_PARAMS = {
        'n_estimators': 200,
        'max_depth': 4,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'reg_alpha': 0.1,
        'reg_lambda': 1.0,
        'objective': 'reg:squarederror',
        'random_state': 42,
        'n_jobs': -1,
    }

    # Walk-Forward 配置
    INITIAL_TRAIN_SIZE = 500   # 初始训练窗口 (~2年)
    TEST_SIZE = 60             # 测试窗口 (~1季度)

    # 信号阈值 (默认值，实际使用自适应阈值)
    BUY_THRESHOLD = 0.1        # 默认买入阈值 (会被自适应阈值覆盖)
    SELL_THRESHOLD = -0.1      # 默认卖出阈值 (会被自适应阈值覆盖)
    THRESHOLD_VOL_FACTOR = 0.12  # 自适应阈值 = 波动率 * 此因子

    # Optuna 配置
    OPTUNA_N_TRIALS = 50       # 搜索次数
    OPTUNA_WF_FOLDS = 3        # Walk-Forward 折数 (用于调优评估)

    def __init__(self, model_params: Optional[dict] = None):
        if not HAS_XGBOOST:
            raise ImportError("xgboost 未安装，请运行: pip install xgboost")
        if not HAS_SKLEARN:
            raise ImportError("scikit-learn 未安装，请运行: pip install scikit-learn")

        self.model_params = model_params or self.DEFAULT_PARAMS.copy()
        self.model = None
        self.feature_columns: List[str] = []
        self._return_std = 1.0  # 收益率标准差，用于 sigmoid 缩放
        self._adaptive_buy_threshold = self.BUY_THRESHOLD
        self._adaptive_sell_threshold = self.SELL_THRESHOLD
        self._flip_signals = False  # 反转模式: IC 持续为负时启用

    # ==================== 自适应阈值 ====================

    def _calculate_adaptive_thresholds(self, returns: pd.Series) -> tuple:
        """
        基于历史收益率波动率计算自适应信号阈值

        不同指数波动率差异较大 (上证50 ~0.7%, 中证500 ~1.0%),
        使用固定阈值会导致低波动指数过度交易、高波动指数信号不足。

        公式: threshold = max(0.05, volatility * THRESHOLD_VOL_FACTOR)

        Args:
            returns: 历史收益率序列 (pct_chg)

        Returns:
            tuple: (buy_threshold, sell_threshold)
        """
        vol = returns.dropna().std()
        if np.isnan(vol) or vol < 0.1:
            vol = 1.0  # 默认波动率 1%

        adaptive_thresh = max(0.05, vol * self.THRESHOLD_VOL_FACTOR)
        return adaptive_thresh, -adaptive_thresh

    # ==================== 特征工程 ====================

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        从技术指标中提取机器学习特征

        Args:
            df: 包含技术指标的 DataFrame

        Returns:
            pd.DataFrame: 新增特征列的 DataFrame
        """
        result = df.copy()

        # --- 数值类型转换（修复字符串类型问题） ---
        numeric_columns = [
            'pct_chg', 'high', 'low', 'close', 'open', 'ma_5', 'ma_10', 'ma_20', 'ma_50',
            'macd', 'macd_histogram', 'macd_signal_line', 'adx', 'plus_di', 'minus_di',
            'rsi', 'kdj_k', 'kdj_d', 'kdj_j', 'atr', 'bb_high', 'bb_low', 'cci',
            'vol', 'vol_ma_5', 'vol_ma_10', 'obv', 'amount', 'pe_ttm', 'pb'
        ]
        for col in numeric_columns:
            if col in result.columns:
                result[col] = pd.to_numeric(result[col], errors='coerce')

        # --- 价格特征 ---
        result['feat_pct_chg'] = result['pct_chg']
        result['feat_intraday_range'] = self._safe_div(
            result['high'] - result['low'], result['close'])
        result['feat_body'] = self._safe_div(
            result['close'] - result['open'], result['close'])
        result['feat_close_ma5'] = self._safe_div(result['close'], result['ma_5'])
        result['feat_close_ma20'] = self._safe_div(result['close'], result['ma_20'])
        result['feat_close_ma50'] = self._safe_div(result['close'], result['ma_50'])

        # --- 趋势特征 ---
        result['feat_ma5_ma10'] = self._safe_div(result['ma_5'], result['ma_10'])
        result['feat_ma10_ma20'] = self._safe_div(result['ma_10'], result['ma_20'])
        result['feat_ma20_ma50'] = self._safe_div(result['ma_20'], result['ma_50'])
        result['feat_macd'] = result['macd']
        result['feat_macd_hist'] = result['macd_histogram']
        result['feat_macd_hist_diff'] = result['macd_histogram'].diff()
        result['feat_adx'] = result.get('adx', pd.Series(dtype=float))
        result['feat_di_diff'] = (
            result.get('plus_di', pd.Series(0, index=result.index))
            - result.get('minus_di', pd.Series(0, index=result.index))
        )

        # --- 动量特征 ---
        result['feat_rsi'] = result['rsi']
        result['feat_kdj_k'] = result['kdj_k']
        result['feat_kdj_d'] = result['kdj_d']
        result['feat_kdj_j'] = result['kdj_j']
        result['feat_rsi_5d_chg'] = result['rsi'].diff(5)

        # --- 波动特征 ---
        result['feat_atr_ratio'] = self._safe_div(
            result.get('atr', pd.Series(dtype=float)), result['close'])
        bb_width = result['bb_high'] - result['bb_low']
        result['feat_bb_position'] = self._safe_div(
            result['close'] - result['bb_low'], bb_width)
        result['feat_cci'] = result.get('cci', pd.Series(dtype=float))

        # --- 成交量特征 ---
        result['feat_vol_ma5_ratio'] = self._safe_div(
            result['vol'], result.get('vol_ma_5', pd.Series(dtype=float)))
        result['feat_vol_ma10_ratio'] = self._safe_div(
            result['vol'], result.get('vol_ma_10', pd.Series(dtype=float)))
        result['feat_obv_5d_slope'] = result['obv'].diff(5) if 'obv' in result.columns else np.nan
        result['feat_amount_chg'] = result['amount'].pct_change() if 'amount' in result.columns else np.nan
        result['feat_vol_chg'] = result['vol'].pct_change()

        # --- 估值特征 ---
        result['feat_pe_ttm'] = result.get('pe_ttm', pd.Series(dtype=float))
        result['feat_pb'] = result.get('pb', pd.Series(dtype=float))
        # 从 JSON 解析百分位
        result['feat_pe_pctl'] = result['percentile_ranks'].apply(
            lambda x: self._extract_json_field(x, 'pe_ttm'))
        result['feat_pb_pctl'] = result['percentile_ranks'].apply(
            lambda x: self._extract_json_field(x, 'pb'))

        # --- 偏离率特征 ---
        for period in [5, 10, 20, 50]:
            result[f'feat_dev_ma{period}'] = result['deviation_rate'].apply(
                lambda x: self._extract_json_field(x, f'ma_{period}'))

        # 收集特征列名
        self.feature_columns = [c for c in result.columns if c.startswith('feat_')]

        return result

    def _create_labels(self, df: pd.DataFrame) -> pd.Series:
        """
        创建标签: 次日实际收益率 (百分比)

        方案B: 直接预测收益率大小（回归任务），而非仅方向
        相比二分类，回归标签保留了收益幅度信息，减少日间噪声影响
        """
        return pd.to_numeric(df['pct_chg'], errors='coerce').shift(-1)

    # ==================== Optuna 超参数自动调优 ====================

    def optimize_hyperparams(self, X: np.ndarray, y: np.ndarray,
                             n_trials: int = None) -> dict:
        """
        使用 Optuna 在 Walk-Forward 框架内搜索最优超参数

        Args:
            X: 特征矩阵
            y: 标签 (次日收益率)
            n_trials: 搜索次数

        Returns:
            dict: 最优参数
        """
        if not HAS_OPTUNA:
            print("  optuna 未安装，跳过超参数调优，使用默认参数")
            return self.model_params

        n_trials = n_trials or self.OPTUNA_N_TRIALS
        n = len(X)

        # Walk-Forward 折数配置
        n_folds = self.OPTUNA_WF_FOLDS
        fold_size = (n - self.INITIAL_TRAIN_SIZE) // n_folds
        if fold_size < 30:
            print("  数据量不足以进行超参数调优，使用默认参数")
            return self.model_params

        def objective(trial):
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 100, 500, step=50),
                'max_depth': trial.suggest_int('max_depth', 2, 7),
                'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.15, log=True),
                'subsample': trial.suggest_float('subsample', 0.5, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.4, 1.0),
                'reg_alpha': trial.suggest_float('reg_alpha', 1e-3, 50.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 1e-3, 50.0, log=True),
                'min_child_weight': trial.suggest_int('min_child_weight', 1, 20),
                'gamma': trial.suggest_float('gamma', 0.0, 5.0),
                'objective': 'reg:squarederror',
                'random_state': 42,
                'n_jobs': -1,
            }

            # Walk-Forward 评估
            all_preds = []
            all_true = []

            for fold in range(n_folds):
                train_end = self.INITIAL_TRAIN_SIZE + fold * fold_size
                test_end = min(train_end + fold_size, n)

                if train_end >= n or test_end <= train_end:
                    continue

                X_train, y_train = X[:train_end], y[:train_end]
                X_test, y_test = X[train_end:test_end], y[train_end:test_end]

                model = xgb.XGBRegressor(**params)
                model.fit(X_train, y_train, verbose=False)
                preds = model.predict(X_test)

                all_preds.extend(preds.tolist())
                all_true.extend(y_test.tolist())

            if len(all_preds) < 10:
                return -1.0

            all_preds_arr = np.array(all_preds)
            all_true_arr = np.array(all_true)

            # 主要目标: IC (信息系数) — 预测值与真实值的相关性
            ic = np.corrcoef(all_preds_arr, all_true_arr)[0, 1]
            if np.isnan(ic):
                ic = 0.0

            # 辅助目标: 方向准确率
            pred_dir = (all_preds_arr > 0).astype(int)
            true_dir = (all_true_arr > 0).astype(int)
            dir_acc = np.mean(pred_dir == true_dir)

            # 综合评分: IC 为主 (70%) + 方向准确率为辅 (30%)
            # IC 范围 [-1, 1]，归一化到 [0, 1]
            score = 0.7 * (ic + 1) / 2.0 + 0.3 * dir_acc
            return score

        print(f"  Optuna 超参数调优中 ({n_trials} trials)...")
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

        best_params = study.best_params
        best_params['objective'] = 'reg:squarederror'
        best_params['random_state'] = 42
        best_params['n_jobs'] = -1

        print(f"  最优综合评分: {study.best_value:.4f}")
        print(f"  最优参数: max_depth={best_params['max_depth']}, "
              f"lr={best_params['learning_rate']:.4f}, "
              f"n_est={best_params['n_estimators']}, "
              f"alpha={best_params['reg_alpha']:.4f}, "
              f"lambda={best_params['reg_lambda']:.4f}, "
              f"min_child_weight={best_params['min_child_weight']}, "
              f"gamma={best_params['gamma']:.4f}")

        return best_params

    # ==================== 训练与预测（避免数据泄露） ====================

    def train_and_predict(self, df: pd.DataFrame, auto_tune: bool = False) -> tuple:
        """
        滚动训练并预测（避免数据泄露）

        核心原则：预测第 i 天时，只用第 i 天之前的数据训练

        Args:
            df: 包含技术指标的原始 DataFrame
            auto_tune: 是否使用 Optuna 自动调优超参数

        Returns:
            tuple: (带预测结果的 DataFrame, 验证指标 dict)
        """
        featured_df = self.prepare_features(df)
        labels = self._create_labels(featured_df)
        n = len(featured_df)

        # 初始化预测列
        preds_all = np.full(n, np.nan)

        # 构建有效数据掩码
        valid_mask = labels.notna()
        for col in self.feature_columns:
            if col in featured_df.columns:
                valid_mask &= featured_df[col].notna()

        valid_indices = np.where(valid_mask)[0]

        if len(valid_indices) < self.INITIAL_TRAIN_SIZE + 10:
            print(f"  数据不足({len(valid_indices)}行有效数据)，无法进行滚动预测")
            result = featured_df.copy()
            result['ml_predicted_return'] = 0.0
            result['ml_probability'] = 0.5
            result['ml_probability_raw'] = 0.5
            result['ml_signal'] = 'HOLD'
            return result, {'note': '数据不足'}

        # 收益率标准差（用于 sigmoid 缩放）
        valid_returns = labels.loc[valid_mask].values
        self._return_std = max(np.nanstd(valid_returns), 0.1)

        # 自适应信号阈值（基于波动率）
        pct_chg_series = pd.to_numeric(df['pct_chg'], errors='coerce')
        buy_thresh, sell_thresh = self._calculate_adaptive_thresholds(pct_chg_series)
        self._adaptive_buy_threshold = buy_thresh
        self._adaptive_sell_threshold = sell_thresh
        print(f"  自适应阈值: BUY>{buy_thresh:.4f}%, SELL<{sell_thresh:.4f}% "
              f"(波动率={pct_chg_series.dropna().std():.3f}%)")

        # Optuna 超参数调优
        if auto_tune:
            X_all = featured_df.iloc[valid_indices][self.feature_columns].values
            y_all = labels.iloc[valid_indices].values
            X_all = np.where(np.isfinite(X_all), X_all, np.nan).astype(np.float32)
            self.model_params = self.optimize_hyperparams(X_all, y_all)

        # 滚动预测
        print(f"  开始滚动预测（回归模式），共 {len(valid_indices)} 条有效数据...")
        all_preds = []
        all_true = []
        train_count = 0

        for i, idx in enumerate(valid_indices):
            # 需要足够的历史数据才能训练
            if i < self.INITIAL_TRAIN_SIZE:
                continue

            # 获取训练数据：只用当前时间点之前的数据
            train_indices = valid_indices[:i]

            # 每隔一定步长重新训练模型（减少计算量）
            if train_count == 0 or train_count >= self.TEST_SIZE:
                X_train = featured_df.iloc[train_indices][self.feature_columns].values
                y_train = labels.iloc[train_indices].values

                X_train = np.where(np.isfinite(X_train), X_train, np.nan).astype(np.float32)

                model = xgb.XGBRegressor(**self.model_params)
                model.fit(X_train, y_train, verbose=False)
                train_count = 0

            train_count += 1

            # 预测当前时间点
            X_pred = featured_df.iloc[[idx]][self.feature_columns].values
            X_pred = np.where(np.isfinite(X_pred), X_pred, np.nan).astype(np.float32)

            pred = model.predict(X_pred)[0]
            preds_all[idx] = pred

            # 记录用于验证指标计算
            all_preds.append(pred)
            all_true.append(labels.iloc[idx])

        # 计算验证指标
        all_preds_arr = np.array(all_preds)
        all_true_arr = np.array(all_true)

        # 方向准确率
        pred_dir = (all_preds_arr > 0).astype(int)
        true_dir = (all_true_arr > 0).astype(int)
        direction_accuracy = np.mean(pred_dir == true_dir)

        # IC (信息系数): 预测值与真实值的相关系数
        ic = np.corrcoef(all_preds_arr, all_true_arr)[0, 1] if len(all_preds_arr) > 1 else 0.0
        if np.isnan(ic):
            ic = 0.0

        # 反转模式检测: 如果 IC 显著为负，翻转预测信号
        self._flip_signals = False
        if ic < -0.02:
            self._flip_signals = True
            print(f"  ⚠ IC={ic:.4f} < -0.02，启用信号反转模式（contrarian mode）")
            # 翻转预测值: 取反
            preds_all = np.where(np.isnan(preds_all), np.nan, -preds_all)
            # 重新计算翻转后的 IC
            flipped_preds = -all_preds_arr
            ic_flipped = np.corrcoef(flipped_preds, all_true_arr)[0, 1]
            if np.isnan(ic_flipped):
                ic_flipped = 0.0
            flipped_dir = (flipped_preds > 0).astype(int)
            direction_accuracy_flipped = np.mean(flipped_dir == true_dir)
            print(f"  反转后 IC: {ic_flipped:.4f}, 方向准确率: {direction_accuracy_flipped:.4f}")

        metrics = {
            'mae': round(mean_absolute_error(all_true_arr, all_preds_arr), 4),
            'rmse': round(np.sqrt(mean_squared_error(all_true_arr, all_preds_arr)), 4),
            'direction_accuracy': round(direction_accuracy, 4),
            'ic': round(ic, 4),
            'ic_abs': round(abs(ic), 4),
            'flip_signals': self._flip_signals,
            'adaptive_buy_threshold': round(buy_thresh, 4),
            'adaptive_sell_threshold': round(sell_thresh, 4),
            'samples': len(all_true_arr),
            'model_type': 'regression',
        }

        # 保存最终模型（用于预测未来）
        valid_X = featured_df.loc[valid_mask, self.feature_columns].values
        valid_y = labels.loc[valid_mask].values
        valid_X = np.where(np.isfinite(valid_X), valid_X, np.nan).astype(np.float32)
        self.model = xgb.XGBRegressor(**self.model_params)
        self.model.fit(valid_X, valid_y, verbose=False)

        # 构建结果 DataFrame
        result = featured_df.copy()
        result['ml_predicted_return'] = preds_all

        # 预测值去均值化: 对于长期偏多或偏空的指数，模型预测可能系统性地偏向一侧
        # 去均值后信号基于"比平时预测更好/更差"，而非绝对收益率
        pred_series = pd.Series(preds_all)
        pred_expanding_mean = pred_series.expanding(min_periods=20).mean()
        preds_demeaned = (pred_series - pred_expanding_mean).values
        result['ml_predicted_return_demeaned'] = preds_demeaned

        # 选择信号源: 检查原始预测是否存在系统性偏差
        valid_raw_preds = preds_all[~np.isnan(preds_all)]
        pred_mean = np.mean(valid_raw_preds) if len(valid_raw_preds) > 0 else 0
        pred_std = np.std(valid_raw_preds) if len(valid_raw_preds) > 0 else 0
        # 如果预测均值偏离0超过1个标准差，说明存在系统性偏差，使用去均值版本
        use_demeaned = abs(pred_mean) > pred_std and pred_std > 0
        if use_demeaned:
            signal_source = preds_demeaned
            print(f"  预测均值偏差: mean={pred_mean:.4f}%, std={pred_std:.4f}% → 启用去均值化信号")
        else:
            signal_source = preds_all

        # 平滑: 如果预测幅度非常小（模型很保守），跳过平滑以保留信号
        signal_std = np.nanstd(signal_source)
        if signal_std < buy_thresh * 0.5:
            preds_smoothed = signal_source.copy()
            print(f"  信号标准差={signal_std:.4f}% 过小，跳过平滑")
        else:
            preds_smoothed = pd.Series(signal_source).rolling(window=3, min_periods=1).mean().values
        result['ml_predicted_return_smoothed'] = preds_smoothed

        # 将预测收益率转换为伪概率 (0-1)，保持与 signal_generator 的兼容性
        result['ml_probability_raw'] = pd.Series(preds_all).apply(
            lambda x: self._return_to_probability(x)).values
        result['ml_probability'] = pd.Series(preds_smoothed).apply(
            lambda x: self._return_to_probability(x)).values

        # 自适应阈值校正: 如果预测幅度普遍小于波动率阈值，使用预测分布来定阈值
        valid_preds_smoothed = preds_smoothed[~np.isnan(preds_smoothed)]
        if len(valid_preds_smoothed) > 0:
            pred_abs = np.abs(valid_preds_smoothed)
            pred_p50 = np.percentile(pred_abs, 50)
            vol_trade_ratio = np.mean(pred_abs > buy_thresh)
            if vol_trade_ratio < 0.10:
                adjusted_thresh = max(0.005, pred_p50)
                print(f"  阈值校正: 波动率阈值{buy_thresh:.4f}%触发率仅{vol_trade_ratio:.1%},"
                      f" 调整为预测P50={adjusted_thresh:.4f}%")
                buy_thresh = adjusted_thresh
                sell_thresh = -adjusted_thresh
                self._adaptive_buy_threshold = buy_thresh
                self._adaptive_sell_threshold = sell_thresh
                metrics['adaptive_buy_threshold'] = round(buy_thresh, 4)
                metrics['adaptive_sell_threshold'] = round(sell_thresh, 4)

        metrics['use_demeaned'] = use_demeaned

        # 存储自适应阈值到 DataFrame，供 signal_generator 使用
        result['ml_buy_threshold'] = buy_thresh
        result['ml_sell_threshold'] = sell_thresh

        # 信号生成: 基于 (去均值+平滑后的) 预测收益率和自适应阈值
        signals = []
        for pred_ret in preds_smoothed:
            if np.isnan(pred_ret):
                signals.append('HOLD')
            elif pred_ret > buy_thresh:
                signals.append('BUY')
            elif pred_ret < sell_thresh:
                signals.append('SELL')
            else:
                signals.append('HOLD')
        result['ml_signal'] = signals

        return result, metrics

    def train(self, df: pd.DataFrame, auto_tune: bool = False) -> dict:
        """
        使用 Walk-Forward 验证训练模型（仅用于验证，不用于预测）

        Args:
            df: 包含技术指标的原始 DataFrame
            auto_tune: 是否使用 Optuna 自动调优超参数

        Returns:
            dict: 验证指标
        """
        featured_df = self.prepare_features(df)
        labels = self._create_labels(featured_df)

        # 去掉最后一行(无标签)和含 NaN 的特征行
        valid_mask = labels.notna()
        for col in self.feature_columns:
            valid_mask &= featured_df[col].notna()

        X = featured_df.loc[valid_mask, self.feature_columns].values
        y = labels.loc[valid_mask].values
        n = len(X)

        X = np.where(np.isfinite(X), X, np.nan).astype(np.float32)
        self._return_std = max(np.nanstd(y), 0.1)

        if n < self.INITIAL_TRAIN_SIZE + self.TEST_SIZE:
            print(f"  数据不足({n}行)，无法进行Walk-Forward验证，使用全量训练")
            self.model = xgb.XGBRegressor(**self.model_params)
            self.model.fit(X, y, verbose=False)
            return {'note': '数据不足，未做交叉验证'}

        # Optuna 超参数调优
        if auto_tune:
            self.model_params = self.optimize_hyperparams(X, y)

        # Walk-Forward
        all_preds = []
        all_true = []

        train_end = self.INITIAL_TRAIN_SIZE
        while train_end + self.TEST_SIZE <= n:
            test_end = min(train_end + self.TEST_SIZE, n)

            X_train, y_train = X[:train_end], y[:train_end]
            X_test, y_test = X[train_end:test_end], y[train_end:test_end]

            model = xgb.XGBRegressor(**self.model_params)
            model.fit(X_train, y_train, verbose=False)

            preds = model.predict(X_test)

            all_preds.extend(preds.tolist())
            all_true.extend(y_test.tolist())

            train_end = test_end

        # 用全量数据训练最终模型
        self.model = xgb.XGBRegressor(**self.model_params)
        self.model.fit(X, y, verbose=False)

        # 汇总验证结果
        all_true_arr = np.array(all_true)
        all_preds_arr = np.array(all_preds)

        pred_dir = (all_preds_arr > 0).astype(int)
        true_dir = (all_true_arr > 0).astype(int)
        direction_accuracy = np.mean(pred_dir == true_dir)

        ic = np.corrcoef(all_preds_arr, all_true_arr)[0, 1] if len(all_preds_arr) > 1 else 0.0
        if np.isnan(ic):
            ic = 0.0

        metrics = {
            'mae': round(mean_absolute_error(all_true_arr, all_preds_arr), 4),
            'rmse': round(np.sqrt(mean_squared_error(all_true_arr, all_preds_arr)), 4),
            'direction_accuracy': round(direction_accuracy, 4),
            'ic': round(ic, 4),
            'samples': len(all_true_arr),
            'model_type': 'regression',
        }
        return metrics

    # ==================== 预测 ====================

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        预测并在 DataFrame 中新增 ml_predicted_return, ml_probability 和 ml_signal 列

        Args:
            df: 包含技术指标的 DataFrame

        Returns:
            pd.DataFrame: 新增预测列的 DataFrame
        """
        result = self.prepare_features(df)

        if self.model is None:
            result['ml_predicted_return'] = 0.0
            result['ml_probability'] = 0.5
            result['ml_signal'] = 'HOLD'
            return result

        X = result[self.feature_columns].values
        X = np.where(np.isfinite(X), X, np.nan).astype(np.float32)

        preds = self.model.predict(X)

        # 如果启用了反转模式，翻转预测值
        if self._flip_signals:
            preds = -preds

        result['ml_predicted_return'] = preds

        # 去均值化 + 平滑 (与 train_and_predict 保持一致)
        pred_series = pd.Series(preds)
        pred_expanding_mean = pred_series.expanding(min_periods=20).mean()
        preds_demeaned = (pred_series - pred_expanding_mean).values

        pred_mean = np.mean(preds)
        pred_std_val = np.std(preds)
        use_demeaned = abs(pred_mean) > pred_std_val and pred_std_val > 0
        signal_source = preds_demeaned if use_demeaned else preds

        signal_std = np.nanstd(signal_source)
        buy_thresh = self._adaptive_buy_threshold
        sell_thresh = self._adaptive_sell_threshold
        if signal_std < buy_thresh * 0.5:
            preds_smoothed = signal_source.copy()
        else:
            preds_smoothed = pd.Series(signal_source).rolling(window=3, min_periods=1).mean().values
        result['ml_predicted_return_smoothed'] = preds_smoothed

        # 转换为伪概率
        result['ml_probability_raw'] = pd.Series(preds).apply(
            lambda x: self._return_to_probability(x)).values
        result['ml_probability'] = pd.Series(preds_smoothed).apply(
            lambda x: self._return_to_probability(x)).values

        # 存储自适应阈值
        result['ml_buy_threshold'] = buy_thresh
        result['ml_sell_threshold'] = sell_thresh

        # 信号生成: 使用自适应阈值
        signals = []
        for pred_ret in preds_smoothed:
            if np.isnan(pred_ret):
                signals.append('HOLD')
            elif pred_ret > buy_thresh:
                signals.append('BUY')
            elif pred_ret < sell_thresh:
                signals.append('SELL')
            else:
                signals.append('HOLD')
        result['ml_signal'] = signals

        return result

    # ==================== 概率转换 ====================

    def _return_to_probability(self, predicted_return: float) -> float:
        """
        将预测收益率转换为 0-1 伪概率

        使用 sigmoid 函数，缩放因子基于历史收益率标准差:
        prob = 1 / (1 + exp(-pred / std * 2))

        当 pred = 0 时，prob = 0.5
        当 pred >> 0 时，prob -> 1.0
        当 pred << 0 时，prob -> 0.0
        """
        if np.isnan(predicted_return):
            return 0.5
        # 缩放因子: 2/std 使得 +/- 1 std 对应约 0.73 / 0.27
        scale = 2.0 / self._return_std
        return 1.0 / (1.0 + np.exp(-predicted_return * scale))

    # ==================== 模型管理 ====================

    def save_model(self, filepath: str):
        """保存模型和特征列名"""
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
        data = {
            'model': self.model,
            'feature_columns': self.feature_columns,
            'model_params': self.model_params,
            'return_std': self._return_std,
        }
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)

    def load_model(self, filepath: str):
        """加载模型和特征列名"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        self.model = data['model']
        self.feature_columns = data['feature_columns']
        self.model_params = data.get('model_params', self.DEFAULT_PARAMS)
        self._return_std = data.get('return_std', 1.0)

    # ==================== 特征重要性 ====================

    def get_feature_importance(self) -> pd.DataFrame:
        """获取特征重要性排名"""
        if self.model is None:
            return pd.DataFrame()

        importance = self.model.feature_importances_
        fi_df = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': importance
        }).sort_values('importance', ascending=False).reset_index(drop=True)
        return fi_df

    # ==================== 工具方法 ====================

    @staticmethod
    def _safe_div(numerator, denominator):
        """安全除法，避免除零，自动处理字符串类型"""
        if isinstance(numerator, pd.Series):
            numerator = pd.to_numeric(numerator, errors='coerce')
        else:
            try:
                numerator = float(numerator) if numerator is not None else np.nan
            except (ValueError, TypeError):
                numerator = np.nan

        if isinstance(denominator, pd.Series):
            denominator = pd.to_numeric(denominator, errors='coerce')
        else:
            try:
                denominator = float(denominator) if denominator is not None else np.nan
            except (ValueError, TypeError):
                denominator = np.nan

        with np.errstate(divide='ignore', invalid='ignore'):
            result = numerator / denominator
        if isinstance(result, pd.Series):
            result = result.replace([np.inf, -np.inf], np.nan)
        return result

    @staticmethod
    def _extract_json_field(json_str, field: str) -> Optional[float]:
        """从 JSON 字符串中提取指定字段"""
        if not json_str or not isinstance(json_str, str):
            return np.nan
        try:
            data = json.loads(json_str)
            val = data.get(field)
            return float(val) if val is not None else np.nan
        except (json.JSONDecodeError, TypeError, ValueError):
            return np.nan
