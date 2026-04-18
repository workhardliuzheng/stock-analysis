"""
V10 下跌区间诊断分析

分析策略在下跌区间的具体表现:
1. 识别所有显著下跌区间 (基准回撤 > 5%)
2. 对比策略 vs 基准在每个区间的表现
3. 分析亏损来源: regime分布、仓位水平、止损触发次数
4. 计算上涨/下跌捕获率 (Upside/Downside Capture Ratio)
5. 识别最大亏损贡献的指数和时段

使用:
    python scripts/analyze_drawdown_periods.py
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from entity import constant


def run_analysis():
    """运行完整诊断分析"""
    print("=" * 70)
    print("  V10 下跌区间诊断分析")
    print("=" * 70)

    # ========== 1. 加载数据并生成信号 ==========
    print("\n[1/6] 加载数据并生成信号...")
    from analysis.index_analyzer import IndexAnalyzer
    from analysis.adaptive_fusion_optimizer import MetaLearner
    from analysis.smart_position_manager import SmartPositionManager, _safe_float

    start_date = '20200101'
    codes = list(constant.TS_CODE_NAME_DICT.keys())
    index_data = {}

    for i, code in enumerate(codes):
        name = constant.TS_CODE_NAME_DICT.get(code, code)
        print(f"  [{i+1}/{len(codes)}] {name}...", end=" ", flush=True)
        try:
            full_start = constant.HISTORY_START_DATE_MAP.get(code, '20100101')
            analyzer = IndexAnalyzer(code, start_date=full_start)
            if len(analyzer.data) < 100:
                print("数据不足，跳过")
                continue
            analyzer.analyze(include_ml=True)
            df = analyzer.data

            # 生成 fused_signal
            required = ['factor_score', 'factor_signal', 'ml_predicted_return', 'ml_signal']
            if all(c in df.columns for c in required):
                meta = MetaLearner(max_trials=10)
                df = meta.generate_fused_signal(df)

            df['trade_date'] = pd.to_datetime(df['trade_date'])
            bt_start = pd.to_datetime(start_date)
            df = df[df['trade_date'] >= bt_start].copy().reset_index(drop=True)

            if len(df) >= 50:
                index_data[code] = df
                print(f"OK ({len(df)} 行)")
            else:
                print("回测区间不足")
        except Exception as e:
            print(f"失败: {e}")

    if len(index_data) < 2:
        print("可用指数不足!")
        return

    # ========== 2. 日期对齐 ==========
    print(f"\n[2/6] 日期对齐 ({len(index_data)} 个指数)...")
    date_sets = [set(df['trade_date'].dt.normalize()) for df in index_data.values()]
    common_dates = sorted(set.intersection(*date_sets))
    print(f"  公共交易日: {len(common_dates)}")
    print(f"  范围: {common_dates[0].strftime('%Y-%m-%d')} ~ {common_dates[-1].strftime('%Y-%m-%d')}")

    aligned = {}
    for code, df in index_data.items():
        df = df.copy()
        df['trade_date'] = df['trade_date'].dt.normalize()
        df = df[df['trade_date'].isin(common_dates)].sort_values('trade_date').reset_index(drop=True)
        for col in ['close', 'pct_chg']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        aligned[code] = df

    # ========== 3. 逐日仿真 (V10 SmartPosition) ==========
    print(f"\n[3/6] 逐日仿真 (V10 SmartPosition)...")
    n_days = len(common_dates)
    signal_col = 'fused_signal'

    # 初始化 SmartPositionManager
    managers = {code: SmartPositionManager() for code in aligned}

    # 预计算背离信号
    div_cache = {}
    for code in aligned:
        div_cache[code] = SmartPositionManager._detect_divergences(aligned[code])

    initial_capital = 100000.0
    portfolio_value = initial_capital
    benchmark_value = initial_capital
    bm_weight = 1.0 / len(aligned)

    portfolio_values = [portfolio_value]
    benchmark_values = [benchmark_value]
    daily_strategy_returns = [0.0]
    daily_benchmark_returns = [0.0]

    # 逐日数据: 仓位、regime、止损事件
    daily_total_position = []
    daily_regime_distribution = []
    daily_stop_loss_events = []  # (date, code)
    daily_index_weights = []

    index_weights = {code: 0.0 for code in aligned}
    prev_target_weights = None

    for t in range(n_days):
        target_weights = {}
        regime_counts = {}
        stop_loss_this_day = []

        for code in aligned:
            df = aligned[code]
            row = df.iloc[t]

            confidence = 0.5
            if 'fused_confidence' in df.columns:
                confidence = _safe_float(row.get('fused_confidence', 0.5), 0.5)
            elif 'fused_score' in df.columns:
                score = _safe_float(row.get('fused_score', 50.0), 50.0)
                confidence = abs(score - 50.0) / 50.0

            div_signal = None
            if code in div_cache and t < len(div_cache[code]):
                div_signal = div_cache[code].iloc[t]

            regime = row.get('regime_label', 'SIDEWAYS')
            regime_counts[regime] = regime_counts.get(regime, 0) + 1

            # 记录止损前仓位
            pre_step_position = managers[code].current_position

            row_data = {
                'fused_signal': row.get(signal_col, 'HOLD'),
                'fused_confidence': confidence,
                'rsi': _safe_float(row.get('rsi', 50.0), 50.0),
                'atr': _safe_float(row.get('atr', 0.0), 0.0),
                'close': _safe_float(row.get('close', 0.0), 0.0),
                'regime_label': regime,
                'vol': _safe_float(row.get('vol', 0.0), 0.0),
                'vol_ma_10': _safe_float(row.get('vol_ma_10', 0.0), 0.0),
                'divergence_signal': div_signal,
            }

            raw_position = managers[code].step(row_data)
            target_weights[code] = raw_position

            # 检测止损事件 (仓位从>0瞬间变为0)
            if pre_step_position > 0.1 and raw_position < 0.01:
                stop_loss_this_day.append(code)

        # 归一化权重
        total_w = sum(target_weights.values())
        if total_w > 1.0:
            factor = 1.0 / total_w
            target_weights = {c: w * factor for c, w in target_weights.items()}

        # T+1 延迟
        if t > 0 and prev_target_weights is not None:
            index_weights = dict(prev_target_weights)

        # 策略收益
        day_return = 0.0
        for code in aligned:
            w = index_weights.get(code, 0.0)
            if w > 0:
                pct = aligned[code].iloc[t].get('pct_chg', 0)
                if pd.notna(pct):
                    day_return += w * float(pct) / 100.0

        # 基准收益
        bm_return = 0.0
        for code in aligned:
            pct = aligned[code].iloc[t].get('pct_chg', 0)
            if pd.notna(pct):
                bm_return += float(pct) / 100.0 * bm_weight

        if t > 0:
            portfolio_value *= (1 + day_return)
            benchmark_value *= (1 + bm_return)
            portfolio_values.append(portfolio_value)
            benchmark_values.append(benchmark_value)
            daily_strategy_returns.append(day_return)
            daily_benchmark_returns.append(bm_return)

        # 记录诊断数据
        total_pos = sum(target_weights.values())
        daily_total_position.append(total_pos)
        daily_regime_distribution.append(dict(regime_counts))
        daily_stop_loss_events.append(stop_loss_this_day)
        daily_index_weights.append(dict(target_weights))

        prev_target_weights = target_weights

    pv = np.array(portfolio_values)
    bv = np.array(benchmark_values)
    sr = np.array(daily_strategy_returns)
    br = np.array(daily_benchmark_returns)
    dates = common_dates[:len(pv)]

    print(f"  仿真完成: {len(pv)} 天")
    total_ret = (pv[-1] - initial_capital) / initial_capital * 100
    bm_ret = (bv[-1] - initial_capital) / initial_capital * 100
    print(f"  策略总收益: {total_ret:+.2f}%")
    print(f"  基准总收益: {bm_ret:+.2f}%")

    # ========== 4. 识别基准下跌区间 ==========
    print(f"\n[4/6] 识别基准下跌区间...")

    # 基准的 rolling max (peak)
    bm_peak = np.maximum.accumulate(bv)
    bm_drawdown = (bv - bm_peak) / bm_peak

    # 识别显著下跌区间 (基准回撤 > 5%)
    in_drawdown = False
    drawdown_periods = []
    dd_start = 0

    for i in range(len(bm_drawdown)):
        if not in_drawdown and bm_drawdown[i] < -0.05:
            in_drawdown = True
            dd_start = i
            # 回溯到 peak
            for j in range(i, -1, -1):
                if bv[j] >= bm_peak[i]:
                    dd_start = j
                    break
        elif in_drawdown and bm_drawdown[i] >= -0.01:
            # 恢复到几乎没有回撤
            in_drawdown = False
            # 找到最低点
            dd_trough = dd_start + np.argmin(bv[dd_start:i+1])
            max_dd = (bv[dd_trough] - bv[dd_start]) / bv[dd_start]
            if max_dd < -0.05:
                drawdown_periods.append({
                    'start_idx': dd_start,
                    'trough_idx': dd_trough,
                    'end_idx': i,
                    'start_date': dates[dd_start],
                    'trough_date': dates[dd_trough],
                    'end_date': dates[i],
                    'bm_drawdown': max_dd,
                })

    # 处理尚未结束的下跌
    if in_drawdown:
        dd_trough = dd_start + np.argmin(bv[dd_start:])
        max_dd = (bv[dd_trough] - bv[dd_start]) / bv[dd_start]
        if max_dd < -0.05:
            drawdown_periods.append({
                'start_idx': dd_start,
                'trough_idx': dd_trough,
                'end_idx': len(bv) - 1,
                'start_date': dates[dd_start],
                'trough_date': dates[dd_trough],
                'end_date': dates[-1],
                'bm_drawdown': max_dd,
            })

    print(f"  发现 {len(drawdown_periods)} 个显著下跌区间 (基准回撤>5%)")

    # ========== 5. 分析每个下跌区间 ==========
    print(f"\n[5/6] 分析每个下跌区间的策略表现...")
    print(f"{'=' * 90}")
    print(f"  {'#':>2} {'开始日期':>12} {'谷底日期':>12} {'结束日期':>12} "
          f"{'基准跌幅':>8} {'策略跌幅':>8} {'改善':>8} {'平均仓位':>8} {'止损次数':>8}")
    print(f"  {'-' * 86}")

    total_bm_loss = 0
    total_st_loss = 0
    period_details = []

    for idx, period in enumerate(drawdown_periods):
        si = period['start_idx']
        ti = period['trough_idx']
        ei = period['end_idx']

        # 策略在同期间的表现 (peak to trough)
        strat_dd = (pv[ti] - pv[si]) / pv[si] if pv[si] > 0 else 0
        bm_dd = period['bm_drawdown']

        # 平均仓位
        avg_pos = np.mean(daily_total_position[si:ti+1])

        # 止损次数
        stop_count = sum(len(events) for events in daily_stop_loss_events[si:ti+1])

        # Regime 分布
        regime_agg = {}
        for day_dist in daily_regime_distribution[si:ti+1]:
            for regime, count in day_dist.items():
                regime_agg[regime] = regime_agg.get(regime, 0) + count
        total_regime = sum(regime_agg.values())

        # 改善幅度
        if bm_dd < 0:
            improvement = (strat_dd - bm_dd) / abs(bm_dd) * 100
        else:
            improvement = 0

        duration_days = ti - si + 1

        print(f"  {idx+1:>2} {period['start_date'].strftime('%Y-%m-%d'):>12} "
              f"{period['trough_date'].strftime('%Y-%m-%d'):>12} "
              f"{period['end_date'].strftime('%Y-%m-%d'):>12} "
              f"{bm_dd*100:>+7.1f}% {strat_dd*100:>+7.1f}% "
              f"{improvement:>+7.1f}% {avg_pos:>7.2f} {stop_count:>8}")

        # Regime 分布细节
        regime_str = ", ".join(f"{k}:{v}" for k, v in
                               sorted(regime_agg.items(), key=lambda x: -x[1]))
        print(f"      Regime: {regime_str}")
        print(f"      持续: {duration_days}天, 区间策略累计日收益: "
              f"{sum(sr[si:ti+1])*100:+.2f}%, 基准: {sum(br[si:ti+1])*100:+.2f}%")

        total_bm_loss += bm_dd * (bv[si] / initial_capital)
        total_st_loss += strat_dd * (pv[si] / initial_capital)

        period_details.append({
            'period': f"#{idx+1}",
            'start': period['start_date'],
            'trough': period['trough_date'],
            'duration': duration_days,
            'bm_dd': bm_dd,
            'strat_dd': strat_dd,
            'improvement': improvement,
            'avg_position': avg_pos,
            'stop_loss_count': stop_count,
            'regime_distribution': regime_agg,
        })

    print(f"  {'-' * 86}")

    # ========== 6. 上涨/下跌捕获率 ==========
    print(f"\n[6/6] 上涨/下跌捕获率分析...")

    # 月度捕获率
    df_monthly = pd.DataFrame({
        'date': dates[1:],
        'strategy': sr[1:],
        'benchmark': br[1:],
    })
    df_monthly['month'] = pd.to_datetime(df_monthly['date']).dt.to_period('M')
    monthly = df_monthly.groupby('month')[['strategy', 'benchmark']].sum()

    up_months = monthly[monthly['benchmark'] > 0]
    down_months = monthly[monthly['benchmark'] <= 0]

    if len(up_months) > 0:
        upside_capture = up_months['strategy'].sum() / up_months['benchmark'].sum() * 100
        up_strategy_avg = up_months['strategy'].mean() * 100
        up_benchmark_avg = up_months['benchmark'].mean() * 100
    else:
        upside_capture = 0
        up_strategy_avg = 0
        up_benchmark_avg = 0

    if len(down_months) > 0 and down_months['benchmark'].sum() != 0:
        downside_capture = down_months['strategy'].sum() / down_months['benchmark'].sum() * 100
        down_strategy_avg = down_months['strategy'].mean() * 100
        down_benchmark_avg = down_months['benchmark'].mean() * 100
    else:
        downside_capture = 0
        down_strategy_avg = 0
        down_benchmark_avg = 0

    print(f"\n  === 月度捕获率 ===")
    print(f"  上涨月份数: {len(up_months)}, 下跌月份数: {len(down_months)}")
    print(f"  上涨捕获率 (Upside Capture):   {upside_capture:.1f}%")
    print(f"    上涨月策略平均: {up_strategy_avg:+.2f}%, 基准平均: {up_benchmark_avg:+.2f}%")
    print(f"  下跌捕获率 (Downside Capture): {downside_capture:.1f}%")
    print(f"    下跌月策略平均: {down_strategy_avg:+.2f}%, 基准平均: {down_benchmark_avg:+.2f}%")
    print(f"  捕获率差 (越高越好):           {upside_capture - downside_capture:+.1f}%")
    print()
    print(f"  [理想状态]: 上涨捕获率 ~100%, 下跌捕获率 ~60% → 差值 +40%")
    print(f"  [当前状态]: 上涨 {upside_capture:.0f}%, 下跌 {downside_capture:.0f}% → 差值 {upside_capture-downside_capture:+.0f}%")

    # 日度分析: 大跌日 vs 大涨日
    print(f"\n  === 日度捕获分析 ===")
    # 大跌日 (基准日跌幅>1%)
    big_down_mask = br < -0.01
    big_up_mask = br > 0.01
    small_mask = ~big_down_mask & ~big_up_mask

    if big_down_mask.sum() > 0:
        big_down_bm = br[big_down_mask].sum() * 100
        big_down_st = sr[big_down_mask].sum() * 100
        print(f"  大跌日 (基准日跌>1%): {big_down_mask.sum()} 天")
        print(f"    基准累计: {big_down_bm:+.2f}%, 策略累计: {big_down_st:+.2f}%, 减损: {big_down_bm-big_down_st:+.2f}%")

    if big_up_mask.sum() > 0:
        big_up_bm = br[big_up_mask].sum() * 100
        big_up_st = sr[big_up_mask].sum() * 100
        print(f"  大涨日 (基准日涨>1%): {big_up_mask.sum()} 天")
        print(f"    基准累计: {big_up_bm:+.2f}%, 策略累计: {big_up_st:+.2f}%, 捕获: {big_up_st/big_up_bm*100:.1f}%")

    if small_mask.sum() > 0:
        small_bm = br[small_mask].sum() * 100
        small_st = sr[small_mask].sum() * 100
        print(f"  小波动日 (|基准日变化|<1%): {small_mask.sum()} 天")
        print(f"    基准累计: {small_bm:+.2f}%, 策略累计: {small_st:+.2f}%")

    # 止损统计
    print(f"\n  === 止损事件统计 ===")
    total_stops = sum(len(e) for e in daily_stop_loss_events)
    print(f"  总止损次数: {total_stops}")

    # 止损后5天内再入场的次数 (鞭打)
    whipsaw_count = 0
    for code in aligned:
        stop_days = []
        for t, events in enumerate(daily_stop_loss_events):
            if code in events:
                stop_days.append(t)
        for sd in stop_days:
            # 检查止损后5天内是否重新建仓
            for check_t in range(sd + 1, min(sd + 6, n_days)):
                w = daily_index_weights[check_t].get(code, 0)
                if w > 0.1:
                    whipsaw_count += 1
                    break

    print(f"  止损后5天内再入场次数 (鞭打): {whipsaw_count}")
    if total_stops > 0:
        print(f"  鞭打率: {whipsaw_count/total_stops*100:.1f}%")

    # 跨指数 BEAR 共识分析
    print(f"\n  === 跨指数 BEAR 共识分析 ===")
    bear_consensus_days = 0
    bear_consensus_details = []
    for t in range(n_days):
        dist = daily_regime_distribution[t]
        n_bear = dist.get('BEAR_TREND', 0) + dist.get('HIGH_VOL', 0)
        n_total = sum(dist.values())
        if n_bear >= 5:
            bear_consensus_days += 1
            # 这天的策略收益
            if t > 0 and t < len(sr):
                bear_consensus_details.append({
                    'date': dates[t] if t < len(dates) else None,
                    'n_bear': n_bear,
                    'strategy_return': sr[t],
                    'benchmark_return': br[t],
                    'total_position': daily_total_position[t],
                })
    print(f"  >=5/8指数处于 BEAR_TREND/HIGH_VOL 的天数: {bear_consensus_days}")
    if bear_consensus_details:
        bcdf = pd.DataFrame(bear_consensus_details)
        print(f"  这些天策略累计收益: {bcdf['strategy_return'].sum()*100:+.2f}%")
        print(f"  这些天基准累计收益: {bcdf['benchmark_return'].sum()*100:+.2f}%")
        print(f"  这些天平均仓位: {bcdf['total_position'].mean():.2f}")

    # MA50 位置分析
    print(f"\n  === 长期趋势 (close vs MA50) 分析 ===")
    below_ma50_all = 0
    below_ma50_loss_days = 0
    above_ma50_all = 0
    below_ma50_strat = 0
    above_ma50_strat = 0
    below_ma50_bm = 0
    above_ma50_bm = 0

    for t in range(1, n_days):
        n_below = 0
        n_total_valid = 0
        for code in aligned:
            df = aligned[code]
            close_val = _safe_float(df.iloc[t].get('close', 0), 0)
            ma50_val = _safe_float(df.iloc[t].get('ma_50', 0), 0)
            if close_val > 0 and ma50_val > 0:
                n_total_valid += 1
                if close_val < ma50_val:
                    n_below += 1

        if n_total_valid > 0:
            pct_below = n_below / n_total_valid
            if pct_below >= 0.6:  # 60%以上指数低于MA50
                below_ma50_all += 1
                if t < len(sr):
                    below_ma50_strat += sr[t]
                    below_ma50_bm += br[t]
            else:
                above_ma50_all += 1
                if t < len(sr):
                    above_ma50_strat += sr[t]
                    above_ma50_bm += br[t]

    print(f"  60%+指数低于MA50的天数: {below_ma50_all}")
    print(f"    策略累计: {below_ma50_strat*100:+.2f}%, 基准累计: {below_ma50_bm*100:+.2f}%")
    print(f"  其余天数: {above_ma50_all}")
    print(f"    策略累计: {above_ma50_strat*100:+.2f}%, 基准累计: {above_ma50_bm*100:+.2f}%")

    # ========== 综合结论 ==========
    print(f"\n{'=' * 70}")
    print(f"  综合诊断结论")
    print(f"{'=' * 70}")
    print(f"\n  [当前保护效果]")
    print(f"    策略最大回撤:  {min((pv - np.maximum.accumulate(pv))/np.maximum.accumulate(pv))*100:+.2f}%")
    print(f"    基准最大回撤:  {min(bm_drawdown)*100:+.2f}%")
    improvement = (1 - abs(min((pv - np.maximum.accumulate(pv))/np.maximum.accumulate(pv))) / abs(min(bm_drawdown))) * 100
    print(f"    回撤改善幅度:  {improvement:+.1f}%")

    print(f"\n  [月度捕获率]")
    print(f"    上涨捕获: {upside_capture:.1f}% | 下跌捕获: {downside_capture:.1f}% | 差值: {upside_capture-downside_capture:+.1f}%")
    target_downside = downside_capture * 0.6
    print(f"    目标下跌捕获(改善40%): {target_downside:.1f}%")

    print(f"\n  [优化空间识别]")
    if whipsaw_count > 5:
        print(f"    [!] 鞭打效应显著: {whipsaw_count}次, 建议增加止损后冷却期")
    if bear_consensus_days > 20:
        print(f"    [!] 系统性熊市天数多: {bear_consensus_days}天, 建议增加跨指数共识保护")
    if below_ma50_all > 100 and below_ma50_strat < 0:
        print(f"    [!] 长期趋势下方亏损: {below_ma50_strat*100:+.2f}%, 建议增加MA趋势过滤")

    print(f"\n{'=' * 70}")


if __name__ == '__main__':
    run_analysis()
