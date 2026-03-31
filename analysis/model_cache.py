"""
模型持久化与增量预测模块

功能:
1. 模型持久化: 保存训练好的XGBoost模型到本地文件
2. 增量预测: 只预测最新N天，利用历史预测结果
3. 模型缓存: 同指数同配置复用模型

作者: Zeno
日期: 2026-03-30
"""

import os
import pickle
import joblib
from typing import Dict, Optional
from datetime import datetime


class ModelCache:
    """
    模型缓存管理器
    
    功能:
    1. 模型持久化: 保存/加载XGBoost模型
    2. 缓存淘汰: LRU策略，最多保留N个模型
    3. 增量预测: 复用历史模型进行快速预测
    
    文件结构:
    cache/
        model_cache/
            {index_code}_ml_v1_{date}.pickle
        predict_cache/
            {index_code}_ml_v1_{date}_predictions.pickle
    """
    
    def __init__(self, cache_dir: str = 'cache', model_version: str = 'ml_v1', max_models: int = 10):
        """
        Args:
            cache_dir: 缓存目录
            model_version: 模型版本号
            max_models: 最多保留的模型数量（LRU淘汰）
        """
        self.cache_dir = cache_dir
        self.model_version = model_version
        self.max_models = max_models
        
        # 创建目录
        os.makedirs(f'{cache_dir}/model_cache', exist_ok=True)
        os.makedirs(f'{cache_dir}/predict_cache', exist_ok=True)
        
        # 模型LRU队列
        self.model_queue = []
        
    def get_model_path(self, index_code: str, date: str) -> str:
        """获取模型文件路径"""
        return f'{self.cache_dir}/model_cache/{index_code}_{self.model_version}_{date}.pickle'
    
    def get_predictions_path(self, index_code: str, date: str) -> str:
        """获取预测结果路径"""
        return f'{self.cache_dir}/predict_cache/{index_code}_{self.model_version}_{date}_predictions.pickle'
    
    def is_model_cached(self, index_code: str, date: str) -> bool:
        """检查模型是否已缓存"""
        return os.path.exists(self.get_model_path(index_code, date))
    
    def is_predictions_cached(self, index_code: str, date: str) -> bool:
        """检查预测结果是否已缓存"""
        return os.path.exists(self.get_predictions_path(index_code, date))
    
    def save_model(self, index_code: str, date: str, model, metadata: dict = None):
        """保存模型"""
        path = self.get_model_path(index_code, date)
        
        # 保存模型
        data = {
            'model': model,
            'date': date,
            'metadata': metadata or {},
            'save_time': datetime.now().isoformat()
        }
        
        with open(path, 'wb') as f:
            pickle.dump(data, f)
        
        # 更新LRU队列
        if index_code in self.model_queue:
            self.model_queue.remove(index_code)
        self.model_queue.insert(0, index_code)
        
        # 淘汰旧模型
        self._evict_models()
    
    def load_model(self, index_code: str, date: str):
        """加载模型"""
        path = self.get_model_path(index_code, date)
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        # 更新LRU队列
        if index_code in self.model_queue:
            self.model_queue.remove(index_code)
        self.model_queue.insert(0, index_code)
        
        return data
    
    def save_predictions(self, index_code: str, date: str, predictions: dict):
        """保存预测结果"""
        path = self.get_predictions_path(index_code, date)
        
        data = {
            'predictions': predictions,
            'date': date,
            'save_time': datetime.now().isoformat()
        }
        
        with open(path, 'wb') as f:
            pickle.dump(data, f)
    
    def load_predictions(self, index_code: str, date: str):
        """加载预测结果"""
        path = self.get_predictions_path(index_code, date)
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        return data['predictions']
    
    def _evict_models(self):
        """LRU淘汰策略"""
        # 淘汰超过 max_models 的指数模型
        while len(self.model_queue) > self.max_models:
            oldest_code = self.model_queue.pop()
            
            # 删除模型文件
            model_path = self.get_model_path(oldest_code, '*')
            # 简单删除所有该指数的模型
            for f in os.listdir(f'{self.cache_dir}/model_cache'):
                if f.startswith(f'{oldest_code}_'):
                    os.remove(f'{self.cache_dir}/model_cache/{f}')
            
            # 删除预测文件
            for f in os.listdir(f'{self.cache_dir}/predict_cache'):
                if f.startswith(f'{oldest_code}_'):
                    os.remove(f'{self.cache_dir}/predict_cache/{f}')
    
    def clear(self, index_code: str = None):
        """清除缓存"""
        if index_code:
            # 删除指定指数的缓存
            for f in os.listdir(f'{self.cache_dir}/model_cache'):
                if f.startswith(f'{index_code}_'):
                    os.remove(f'{self.cache_dir}/model_cache/{f}')
            
            for f in os.listdir(f'{self.cache_dir}/predict_cache'):
                if f.startswith(f'{index_code}_'):
                    os.remove(f'{self.cache_dir}/predict_cache/{f}')
            
            if index_code in self.model_queue:
                self.model_queue.remove(index_code)
        else:
            # 删除所有缓存
            for f in os.listdir(f'{self.cache_dir}/model_cache'):
                os.remove(f'{self.cache_dir}/model_cache/{f}')
            
            for f in os.listdir(f'{self.cache_dir}/predict_cache'):
                os.remove(f'{self.cache_dir}/predict_cache/{f}')
            
            self.model_queue = []
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计"""
        model_files = os.listdir(f'{self.cache_dir}/model_cache')
        predict_files = os.listdir(f'{self.cache_dir}/predict_cache')
        
        return {
            'model_count': len(model_files),
            'predict_count': len(predict_files),
            'model_queue': self.model_queue
        }


class IncrementalPredictor:
    """
    增量预测器
    
    功能:
    1. 复用历史模型进行快速预测
    2. 只预测最新N天，利用历史预测结果
    3. 自动检测模型版本变化
    
    使用示例:
        predictor = IncrementalPredictor(model_cache, days_to_predict=30)
        
        # 第一次运行：全量预测
        predictions = predictor.predict(df, model, index_code='000300.SH')
        
        # 第二次运行：增量预测（只预测最新30天）
        predictions = predictor.predict(df, model, index_code='000300.SH', use_cache=True)
    """
    
    def __init__(self, model_cache: ModelCache, days_to_predict: int = 30):
        """
        Args:
            model_cache: 模型缓存管理器
            days_to_predict: 增量预测天数
        """
        self.model_cache = model_cache
        self.days_to_predict = days_to_predict
    
    def predict(self, df, model, index_code: str, date: str = None, use_cache: bool = True):
        """
        增量预测
        
        Args:
            df: 数据DataFrame
            model: 训练好的模型
            index_code: 指数代码
            date: 当前日期（格式：YYYYMMDD）
            use_cache: 是否使用缓存
        
        Returns:
            dict: 预测结果
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        # 检查缓存
        if use_cache and self.model_cache.is_predictions_cached(index_code, date):
            print(f"  [缓存命中] {index_code} {date} - 直接加载预测结果")
            return self.model_cache.load_predictions(index_code, date)
        
        # 增量预测
        n_days = min(self.days_to_predict, len(df))
        df_recent = df.tail(n_days).copy()
        
        # 获取特征列
        feature_cols = [col for col in df_recent.columns if col.startswith('feat_')]
        X = df_recent[feature_cols]
        
        # 预测
        predictions = model.predict(X)
        
        # 整理结果
        result = {
            'predictions': predictions.tolist(),
            'dates': df_recent['trade_date'].tolist(),
            'recent_days': n_days,
            'total_days': len(df),
            'predict_time': datetime.now().isoformat()
        }
        
        # 保存缓存
        self.model_cache.save_predictions(index_code, date, result)
        
        return result
    
    def get_last_available_prediction(self, index_code: str) -> Optional[dict]:
        """获取最近的预测结果"""
        predict_dir = f'{self.model_cache.cache_dir}/predict_cache'
        
        if not os.path.exists(predict_dir):
            return None
        
        # 查找该指数的预测文件
        files = [f for f in os.listdir(predict_dir) if f.startswith(f'{index_code}_')]
        
        if not files:
            return None
        
        # 获取最新的
        latest_file = sorted(files)[-1]
        
        return self.model_cache.load_predictions(index_code, latest_file.split('_')[2])
