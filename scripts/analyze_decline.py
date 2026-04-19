"""V13 主下跌段买卖/仓位分析"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from analysis.portfolio_backtester import PortfolioBacktester
from entity import constant

# Run backtester to get raw simulation data
bt = PortfolioBacktester(
    start_date='20200102',
    end_date=None,
    signal_column='fused_signal',
    use_smart_position=True,
    cross_index_consensus_enabled=True,
    include_macro=True
)

index_data = bt._load_all_indices()
common_dates, aligned_data = bt._align_dates(index_data)
actual_signal_col = bt._resolve_signal_column(aligned_data)

from analysis.smart_position_manager import SmartPositionManager
for code in aligned_data.keys():
    bt._smart_managers[code] = SmartPositionManager()

sim = bt._simulate(aligned_data, common_dates, actual_signal_col)

date_strs = [d.strftime('%Y-%m-%d') for d in common_dates]
pv = sim['portfolio_values']
bv = sim['benchmark_values']
weights_hist = sim['index_weights_history']
events = sim['trade_events']

print('=' * 70)
print('  V13 主下跌段分析 (2021-12 ~ 2024-09)')
print('=' * 70)

decline_start = None
decline_end = None
for i, d in enumerate(date_strs):
    if d >= '2021-12-01' and decline_start is None:
        decline_start = i
    if d <= '2024-09-30':
        decline_end = i

print(f'  下跌段: {date_strs[decline_start]} ~ {date_strs[decline_end]}')
print(f'  交易日数: {decline_end - decline_start + 1}')
print(f'  策略净值: {pv[decline_start]:.0f} -> {pv[decline_end]:.0f} ({(pv[decline_end]/pv[decline_start]-1)*100:+.2f}%)')
print(f'  基准净值: {bv[decline_start]:.0f} -> {bv[decline_end]:.0f} ({(bv[decline_end]/bv[decline_start]-1)*100:+.2f}%)')

decline_buys = [e for e in events if decline_start <= e['day_idx'] <= decline_end and e['type'] == 'BUY']
decline_sells = [e for e in events if decline_start <= e['day_idx'] <= decline_end and e['type'] == 'SELL']
n_days = decline_end - decline_start + 1
print(f'\n  买入事件: {len(decline_buys)} 次')
print(f'  卖出事件: {len(decline_sells)} 次')
print(f'  总操作: {len(decline_buys) + len(decline_sells)} 次 / {n_days} 天 = {(len(decline_buys)+len(decline_sells))/n_days*100:.1f}%天有操作')

total_weights = []
for i in range(decline_start, decline_end + 1):
    if i < len(weights_hist):
        tw = sum(weights_hist[i].values())
        total_weights.append(tw)

tw_arr = np.array(total_weights)
print(f'\n  --- 仓位统计 ---')
print(f'  平均总仓位: {tw_arr.mean()*100:.1f}%')
print(f'  最大总仓位: {tw_arr.max()*100:.1f}%')
print(f'  最小总仓位: {tw_arr.min()*100:.1f}%')
print(f'  零仓位天数: {(tw_arr < 0.01).sum()} ({(tw_arr < 0.01).sum()/n_days*100:.1f}%)')
print(f'  >50%仓位天数: {(tw_arr > 0.5).sum()} ({(tw_arr > 0.5).sum()/n_days*100:.1f}%)')
print(f'  >80%仓位天数: {(tw_arr > 0.8).sum()} ({(tw_arr > 0.8).sum()/n_days*100:.1f}%)')

# 按季度仓位
print(f'\n  --- 按季度仓位 ---')
quarters = {}
for i in range(decline_start, decline_end + 1):
    if i < len(weights_hist):
        d = date_strs[i]
        q = d[:4] + '-Q' + str((int(d[5:7])-1)//3 + 1)
        if q not in quarters:
            quarters[q] = {'weights': [], 'buys': 0, 'sells': 0}
        quarters[q]['weights'].append(sum(weights_hist[i].values()))

for e in events:
    if decline_start <= e['day_idx'] <= decline_end:
        d = date_strs[e['day_idx']]
        q = d[:4] + '-Q' + str((int(d[5:7])-1)//3 + 1)
        if q in quarters:
            if e['type'] == 'BUY':
                quarters[q]['buys'] += 1
            else:
                quarters[q]['sells'] += 1

for q in sorted(quarters.keys()):
    vals = np.array(quarters[q]['weights'])
    buys = quarters[q]['buys']
    sells = quarters[q]['sells']
    print(f'  {q}: 平均仓位={vals.mean()*100:.1f}%, 买={buys}, 卖={sells}, 天数={len(vals)}')

# 各指数平均仓位
print(f'\n  --- 各指数平均仓位(下跌段) ---')
codes = list(aligned_data.keys())
for code in codes:
    name = constant.TS_CODE_NAME_DICT.get(code, code)
    code_weights = []
    for i in range(decline_start, decline_end + 1):
        if i < len(weights_hist):
            code_weights.append(weights_hist[i].get(code, 0.0))
    cw = np.array(code_weights)
    if cw.mean() > 0.001:
        print(f'  {name:8s}: 平均={cw.mean()*100:.1f}%, >0天数={int((cw>0.01).sum())} ({(cw>0.01).sum()/len(cw)*100:.0f}%)')

# 交易事件明细 (前25条+后10条)
all_decline_events = sorted(
    [e for e in events if decline_start <= e['day_idx'] <= decline_end],
    key=lambda x: x['day_idx']
)
print(f'\n  --- 下跌段交易事件明细 (共{len(all_decline_events)}条) ---')
show_events = all_decline_events[:25]
if len(all_decline_events) > 35:
    show_events = all_decline_events[:25] + [None] + all_decline_events[-10:]

for e in show_events:
    if e is None:
        print(f'  ... (省略 {len(all_decline_events)-35} 条) ...')
        continue
    idx = e['day_idx']
    d = date_strs[idx]
    tw = sum(weights_hist[idx].values()) if idx < len(weights_hist) else 0
    pval = pv[idx] if idx < len(pv) else 0
    print(f'  {d}  {e["type"]:4s}  净变化={e["net_change"]:+.3f}  总仓位={tw*100:.1f}%  净值={pval:.0f}')

# 最大回撤期间仓位快照
print(f'\n  --- 最大回撤期间仓位快照 ---')
pv_arr = np.array(pv[decline_start:decline_end+1])
running_max = np.maximum.accumulate(pv_arr)
drawdowns = (pv_arr - running_max) / running_max
trough_idx = np.argmin(drawdowns)
peak_idx = np.argmax(pv_arr[:trough_idx+1]) if trough_idx > 0 else 0
print(f'  回撤顶点: {date_strs[decline_start+peak_idx]} 净值={pv_arr[peak_idx]:.0f}')
print(f'  回撤谷底: {date_strs[decline_start+trough_idx]} 净值={pv_arr[trough_idx]:.0f}')
print(f'  回撤幅度: {(pv_arr[trough_idx]/pv_arr[peak_idx]-1)*100:.2f}%')

n_snap = min(25, trough_idx - peak_idx + 1)
step = max(1, (trough_idx - peak_idx) // n_snap)
print(f'\n  回撤区间仓位走势:')
for j in range(peak_idx, trough_idx + step, step):
    if j >= len(pv_arr):
        break
    gi = decline_start + j
    if gi < len(weights_hist):
        tw = sum(weights_hist[gi].values())
        chg = (pv_arr[j]/pv_arr[peak_idx]-1)*100
        print(f'  {date_strs[gi]}  总仓位={tw*100:.1f}%  净值={pv_arr[j]:.0f}  vs顶点={chg:+.2f}%')

print('\n  [分析完成]')
