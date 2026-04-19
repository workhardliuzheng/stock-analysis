"""V13 宏观因子 - 单指数端到端测试"""
import sys
sys.path.insert(0, '.')

from analysis.index_analyzer import IndexAnalyzer

# 用沪深300测试, 较短历史加快速度
analyzer = IndexAnalyzer('000300.SH', start_date='20200101', include_macro=True)
print(f'数据加载: {len(analyzer.data)} 行')
df = analyzer.analyze(include_ml=True)
print(f'分析完成: {len(df)} 行')

# 检查宏观列是否存在
macro_cols = [c for c in df.columns if 'macro' in c.lower()]
print(f'宏观列: {macro_cols}')

if 'macro_score' in df.columns:
    ms = df['macro_score']
    print(f'宏观评分: 最新={ms.iloc[-1]:.1f}, 均值={ms.mean():.1f}')

if 'regime_macro_score' in df.columns:
    rms = df['regime_macro_score']
    print(f'Regime宏观: 最新={rms.iloc[-1]:.1f}')

# 检查ML特征中是否包含宏观
feat_cols = [c for c in df.columns if c.startswith('feat_macro')]
print(f'ML宏观特征: {feat_cols}')

sig = analyzer.get_current_signal()
fs = sig.get('final_signal', 'N/A')
fc = sig.get('final_confidence', 0)
print(f'信号: {fs} 置信度: {fc:.2f}')
