#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主分析流程 - 统一动态权重优化

功能:
1. 对每个指数独立进行Walk-Forward权重优化
2. 将最优权重保存到数据库
3. 所有回测使用相同的权重逻辑（从数据库读取）
4. 回测结果明确显示权重分配
"""

import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from analysis.index_analyzer import IndexAnalyzer
from analysis.adaptive_fusion_optimizer import MetaLearner
from mysql_connect.db import get_engine
from sqlalchemy import text

def optimize_and_save_weights(code, name, df):
    """
    为单个指数优化并保存最优权重
    
    Args:
        code: 指数代码
        name: 指数名称
        df: DataFrame (包含必要列)
    
    Returns:
        dict: 最优权重
    """
    print(f"\n[optimize] 正在为 {name} ({code}) 优化权重...")
    
    try:
        # 1. 准备数据
        required_cols = ['factor_score', 'factor_signal', 'ml_predicted_return', 'ml_signal', 'pct_chg']
        if not all(col in df.columns for col in required_cols):
            print(f"    [WARN] 缺少必要列，跳过优化")
            return None
        
        # 2. 创建MetaLearner (使用正确的参数)
        learner = MetaLearner(
            initial_train_size=500,
            test_size=60, 
            max_trials=50,
            market_state='oscillation'
        )
        learner._df = df.copy()
        
        # 3. 预处理信号
        learner._df['factor_signal'] = learner._df['factor_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)
        learner._df['ml_signal'] = learner._df['ml_signal'].map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)
        
        # 4. 优化
        optimal_weights, best_sharpe = learner.optimize(df)
        
        if optimal_weights:
            print(f"    [OK] 最优权重: {optimal_weights}")
            print(f"    [OK] 最优夏普比率: {best_sharpe:.4f}")
            
            # 5. 保存到数据库
            save_weights_to_db(code, name, optimal_weights, best_sharpe)
            
            return optimal_weights
        else:
            print(f"    [WARN] 优化失败，使用默认权重")
            return get_default_weights()
            
    except Exception as e:
        print(f"    [ERROR] 优化失败: {e}")
        return get_default_weights()

def save_weights_to_db(code, name, weights, sharpe):
    """保存权重到数据库"""
    import os
    import sys
    
    # 设置PYTHONPATH（运行时需要）
    if 'E:\\pycharm\\stock-analysis' not in sys.path:
        sys.path.insert(0, r'E:\pycharm\stock-analysis')
    
    from mysql_connect.db import get_engine
    from sqlalchemy import text
    
    engine = get_engine()
    
    insert_sql = """
    INSERT INTO v75_optimal_weights (ts_code, name, factor_score, factor_signal, ml_return, ml_signal, best_sharpe, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
    ON DUPLICATE KEY UPDATE
        factor_score = VALUES(factor_score),
        factor_signal = VALUES(factor_signal),
        ml_return = VALUES(ml_return),
        ml_signal = VALUES(ml_signal),
        best_sharpe = VALUES(best_sharpe),
        updated_at = VALUES(updated_at)
    """
    
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            conn.execute(text(insert_sql), (
                code, name, 
                weights.get('factor_score', 0),
                weights.get('factor_signal', 0),
                weights.get('ml_return', 0),
                weights.get('ml_signal', 0),
                sharpe
            ))
            trans.commit()
            print(f"    [OK] 权重已保存到数据库")
    except Exception as e:
        print(f"    [WARN] 保存失败: {e}")

def get_default_weights():
    """默认权重"""
    return {
        'factor_score': 0.70,
        'factor_signal': 0.05,
        'ml_return': 0.20,
        'ml_signal': 0.05,
    }

def signal_all_indices_with_optimization():
    """带权重优化的信号生成主流程"""
    from entity import constant
    
    print("=" * 60)
    print("AAAAA 主分析流程 - 统一动态权重优化 AAAAA")
    print("=" * 60)
    
    for ts_code in constant.TS_CODE_LIST:
        try:
            print(f"\n{'='*60}")
            print(f"[START] 分析 {constant.TS_CODE_NAME_DICT.get(ts_code, ts_code)} ({ts_code})")
            print(f"{'='*60}")
            
            # 1. 分析数据（不进行ML优化）
            analyzer = IndexAnalyzer(ts_code)
            df = analyzer.analyze(include_ml=True, auto_tune=False)
            
            # 2. 权重优化
            weights = optimize_and_save_weights(
                ts_code, 
                constant.TS_CODE_NAME_DICT.get(ts_code, ts_code), 
                df
            )
            
            # 3. 使用优化后的权重生成融合信号
            if weights:
                # TODO: 应用优化权重到融合信号
                print(f"    [INFO] 权重已保存，待应用于融合信号")
            
            print(f"[OK] {constant.TS_CODE_NAME_DICT.get(ts_code, ts_code)} 分析完成")
            
        except Exception as e:
            print(f"[ERROR] {constant.TS_CODE_NAME_DICT.get(ts_code, ts_code)} 分析失败: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    signal_all_indices_with_optimization()
