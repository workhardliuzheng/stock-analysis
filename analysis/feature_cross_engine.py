"""
特征交叉工程模块

生成特征交叉项、比率特征、多项式组合特征，
提升模型预测能力。

作者: Zeno
日期: 2026-03-30
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime


class FeatureCrossEngine:
    """
    特征交叉引擎
    
    功能:
    1. 生成特征交叉项（乘法）
    2. 生成比率特征（除法）
    3. 生成多项式特征（degree=2）
    4. 特征重要性筛选
    
    使用示例:
        engine = FeatureCrossEngine()
        
        # 生成交叉特征
        df_with_cross = engine.add_cross_features(
            df, 
            features=['RSI', 'MACD', 'PE'],
            operations=['multiply', 'divide']
        )
        
        # 生成多项式特征
        df_with_poly = engine.add_polynomial_features(df, degree=2)
    """
    
    def __init__(self, cross_features: List[tuple] = None):
        """
        Args:
            cross_features: 预定义的交叉特征列表 [(feat1, feat2, op), ...]
        """
        self.cross_features = cross_features or [
            # RSI相关
            ('feat_rsi_5d_chg', 'feat_macd', 'multiply'),
            ('feat_rsi_5d_chg', 'feat_bb_position', 'multiply'),
            # MACD相关
            ('feat_macd', 'feat_macd_hist_diff', 'multiply'),
            ('feat_macd_hist_diff', 'feat_pct_chg', 'multiply'),
            # 均线相关
            ('feat_ma5_ma10', 'feat_rsi_5d_chg', 'multiply'),
            ('feat_ma10_ma20', 'feat_macd', 'multiply'),
            # 估值相关
            ('feat_pe_ttm', 'feat_pb', 'multiply'),
            ('feat_pe_pctl', 'feat_rsi_5d_chg', 'multiply'),
            # 成交量相关
            ('feat_obv_5d_slope', 'feat_pct_chg', 'multiply'),
            ('feat_volume_5d_chg', 'feat_pct_chg', 'multiply'),
            # 波动率相关
            ('feat_atr_ratio', 'feat_pct_chg', 'multiply'),
            ('feat_intraday_range', 'feat_pct_chg', 'multiply'),
        ]
    
    def add_cross_features(self, df: pd.DataFrame, 
                          features: List[str] = None,
                          operations: List[str] = None) -> pd.DataFrame:
        """
        添加特征交叉项
        
        Args:
            df: 原始DataFrame
            features: 要交叉的特征列表（None表示自动检测feat_开头的特征）
            operations: 操作类型 ['multiply', 'divide', 'add', 'subtract']
        
        Returns:
            pd.DataFrame: 添加交叉特征后的DataFrame
        """
        df_result = df.copy()
        
        # 自动检测特征
        if features is None:
            features = [col for col in df_result.columns if col.startswith('feat_')]
        
        # 默认操作
        if operations is None:
            operations = ['multiply', 'divide']
        
        # 生成交叉特征
        feature_names = []
        for i, feat1 in enumerate(features):
            for feat2 in features[i+1:]:  # 避免重复
                for op in operations:
                    new_feat = self._create_cross_feature(df_result, feat1, feat2, op)
                    if new_feat:
                        feature_names.append(new_feat)
        
        print(f"  交叉特征: 生成 {len(feature_names)} 个新特征")
        return df_result, feature_names
    
    def _create_cross_feature(self, df: pd.DataFrame, feat1: str, feat2: str, op: str) -> Optional[str]:
        """创建单个交叉特征"""
        new_name = f'feat_{feat1.replace("feat_", "")}_{op}_{feat2.replace("feat_", "")}'
        
        if new_name in df.columns:
            return None  # 避免重复
        
        try:
            if op == 'multiply':
                df[new_name] = df[feat1] * df[feat2]
            elif op == 'divide':
                df[new_name] = df[feat1] / (df[feat2] + 1e-8)  # 避免除零
            elif op == 'add':
                df[new_name] = df[feat1] + df[feat2]
            elif op == 'subtract':
                df[new_name] = df[feat1] - df[feat2]
            else:
                return None
            
            return new_name
        except Exception as e:
            print(f"  [警告] 创建特征 {new_name} 失败: {e}")
            return None
    
    def add_ratio_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加比率特征
        
        Args:
            df: 原始DataFrame
        
        Returns:
            pd.DataFrame: 添加比率特征后的DataFrame
        """
        df_result = df.copy()
        
        ratio_features = [
            # 价格比率
            ('close', 'ma5', 'feat_close_ma5'),
            ('close', 'ma10', 'feat_close_ma10'),
            ('close', 'ma20', 'feat_close_ma20'),
            ('close', 'ma50', 'feat_close_ma50'),
            ('close', 'ma200', 'feat_close_ma200'),
            # 价格波动比率
            ('intraday_range', 'close', 'feat_intraday_range_ratio'),
            ('atr_ratio', 'close', 'feat_atr_ratio_price'),
            # 成交量比率
            ('vol', 'ma_vol_5', 'feat_vol_ma5_ratio'),
            ('vol', 'ma_vol_20', 'feat_vol_ma20_ratio'),
            # 成交金额比率
            ('amount', 'close', 'feat_amount_close_ratio'),
        ]
        
        count = 0
        for num, den, new_name in ratio_features:
            if num in df_result.columns and den in df_result.columns:
                try:
                    df_result[new_name] = df_result[num] / (df_result[den] + 1e-8)
                    count += 1
                except Exception as e:
                    print(f"  [警告] 创建比率特征 {new_name} 失败: {e}")
        
        print(f"  比率特征: 生成 {count} 个新特征")
        return df_result
    
    def add_polynomial_features(self, df: pd.DataFrame, degree: int = 2) -> pd.DataFrame:
        """
        添加多项式特征
        
        Args:
            df: 原始DataFrame
            degree: 多项式次数（默认2）
        
        Returns:
            pd.DataFrame: 添加多项式特征后的DataFrame
        """
        df_result = df.copy()
        
        # 选择数值型特征
        numeric_cols = df_result.select_dtypes(include=[np.number]).columns.tolist()
        feat_cols = [col for col in numeric_cols if col.startswith('feat_')]
        
        count = 0
        for feat in feat_cols:
            if feat.replace('feat_', '') in ['pct_chg', 'close', 'volume', 'amount']:
                continue  # 跳过大基数特征
            
            # 平方项
            if degree >= 2:
                new_name = f'{feat}_sq'
                if new_name not in df_result.columns:
                    try:
                        df_result[new_name] = df_result[feat] ** 2
                        count += 1
                    except Exception as e:
                        print(f"  [警告] 创建平方特征 {new_name} 失败: {e}")
            
            # 立方项（可选）
            if degree >= 3:
                new_name = f'{feat}_cube'
                if new_name not in df_result.columns:
                    try:
                        df_result[new_name] = df_result[feat] ** 3
                        count += 1
                    except Exception as e:
                        print(f"  [警告] 创建立方特征 {new_name} 失败: {e}")
        
        print(f"  多项式特征: 生成 {count} 个新特征")
        return df_result
    
    def add_log_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加对数特征（适用于偏态分布）
        
        Args:
            df: 原始DataFrame
        
        Returns:
            pd.DataFrame: 添加对数特征后的DataFrame
        """
        df_result = df.copy()
        
        log_features = [
            'feat_volume_5d_chg', 'feat_amount', 'feat_vol',
            'feat_pe_ttm', 'feat_pb', 'feat_turnover_rate'
        ]
        
        count = 0
        for feat in log_features:
            if feat in df_result.columns:
                new_name = f'{feat}_log'
                try:
                    df_result[new_name] = np.log1p(df_result[feat].clip(lower=0))
                    count += 1
                except Exception as e:
                    print(f"  [警告] 创建对数特征 {new_name} 失败: {e}")
        
        print(f"  对数特征: 生成 {count} 个新特征")
        return df_result
    
    def generate_all_features(self, df: pd.DataFrame) -> tuple:
        """
        生成所有特征（交叉+比率+多项式+对数）
        
        Args:
            df: 原始DataFrame
        
        Returns:
            tuple: (生成后的DataFrame, 新特征列表)
        """
        df_result = df.copy()
        all_new_features = []
        
        # 1. 交叉特征
        df_result, cross_features = self.add_cross_features(df_result)
        all_new_features.extend(cross_features)
        
        # 2. 比率特征
        df_result = self.add_ratio_features(df_result)
        ratio_features = [col for col in df_result.columns if col.startswith('feat_') and col not in df.columns and col not in cross_features]
        all_new_features.extend(ratio_features)
        
        # 3. 多项式特征
        df_result = self.add_polynomial_features(df_result)
        poly_features = [col for col in df_result.columns if col.startswith('feat_') and col not in df.columns and col not in cross_features + ratio_features]
        all_new_features.extend(poly_features)
        
        # 4. 对数特征
        df_result = self.add_log_features(df_result)
        log_features = [col for col in df_result.columns if col.startswith('feat_') and col not in df.columns and col not in cross_features + ratio_features + poly_features]
        all_new_features.extend(log_features)
        
        return df_result, all_new_features


def select_important_features(df: pd.DataFrame, labels: np.ndarray, 
                             n_features: int = 50) -> tuple:
    """
    选择最重要特征（综合多种方法）
    
    Args:
        df: DataFrame
        labels: 标签数组
        n_features: 保留的特征数量
    
    Returns:
        tuple: (筛选后的DataFrame, 特征列表)
    """
    import numpy as np
    import pandas as pd
    
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.feature_selection import mutual_info_regression
    
    # 选择数值特征
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feat_cols = [col for col in numeric_cols if col.startswith('feat_')]
    
    if len(feat_cols) <= n_features:
        return df, feat_cols
    
    print(f"  特征筛选: 从 {len(feat_cols)} 个特征中筛选出 {n_features} 个")
    
    # 1. 随机森林特征重要性
    rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(df[feat_cols].fillna(0), labels)
    rf_importance = rf.feature_importances_
    
    # 2. 互信息
    mi = mutual_info_regression(df[feat_cols].fillna(0), labels, random_state=42)
    
    # 3. 综合评分
    scores = {}
    for i, feat in enumerate(feat_cols):
        scores[feat] = {
            'rf': rf_importance[i],
            'mi': mi[i]
        }
    
    # 排序并选择
    sorted_features = sorted(scores.keys(), key=lambda x: scores[x]['rf'] + scores[x]['mi'], reverse=True)
    selected_features = sorted_features[:n_features]
    
    print(f"  选中特征: {len(selected_features)} 个")
    
    return df[selected_features + [col for col in df.columns if not col.startswith('feat_')]], selected_features
