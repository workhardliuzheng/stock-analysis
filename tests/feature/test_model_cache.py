"""
测试模型持久化与增量预测功能
"""

import sys
sys.path.insert(0, '.')

from analysis.model_cache import ModelCache, IncrementalPredictor

if __name__ == '__main__':
    print("=" * 80)
    print("测试模型持久化与增量预测功能")
    print("=" * 80)
    
    # 测试 ModelCache
    print("\n【测试1】ModelCache 模型缓存管理器")
    print("-" * 60)
    cache = ModelCache(cache_dir='test_cache')
    
    # 创建假模型数据
    import pickle
    import numpy as np
    from datetime import datetime
    
    class FakeModel:
        def __init__(self):
            self.feature_importances_ = np.array([0.1] * 10)
        
        def predict(self, X):
            return np.random.randn(len(X))
    
    fake_model = FakeModel()
    metadata = {
        'feature_columns': [f'feat_{i}' for i in range(10)],
        'test_time': datetime.now().isoformat()
    }
    
    # 保存模型
    cache.save_model('000300.SH', '20260330', fake_model, metadata)
    print(f"  保存模型: 000300.SH 20260330")
    
    # 验证缓存
    assert cache.is_model_cached('000300.SH', '20260330'), "模型缓存失败"
    print(f"  缓存验证: OK")
    
    # 加载模型
    loaded = cache.load_model('000300.SH', '20260330')
    print(f"  加载模型: 成功")
    
    # 测试 IncrementalPredictor
    print("\n【测试2】IncrementalPredictor 增量预测")
    print("-" * 60)
    predictor = IncrementalPredictor(cache, days_to_predict=30)
    
    # 创建假数据
    import pandas as pd
    df = pd.DataFrame({
        'trade_date': list(range(1, 101)),
        'feat_0': np.random.randn(100),
        'feat_1': np.random.randn(100),
        'feat_2': np.random.randn(100),
    })
    
    # 预测
    predictions = predictor.predict(df, fake_model, '000300.SH', '20260330', use_cache=False)
    print(f"  预测天数: {predictions['recent_days']}")
    print(f"  总数据: {predictions['total_days']}条")
    
    # 验证缓存命中
    predictions2 = predictor.predict(df, fake_model, '000300.SH', '20260330', use_cache=True)
    print(f"  缓存命中: OK")
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)
