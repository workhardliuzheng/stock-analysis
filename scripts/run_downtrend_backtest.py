"""V12 downtrend period backtest: 2023-04-01 to 2024-09-26"""
import sys
import os
import io

# Force UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.index_analyzer import portfolio_backtest

print("=" * 60)
print("V12 Downtrend Backtest: 20230401 - 20240926")
print("=" * 60)

result = portfolio_backtest(
    start_date='20230401',
    end_date='20240926',
    cross_index_consensus=True,
)

print("\n" + "=" * 60)
print("DONE")
print("=" * 60)
