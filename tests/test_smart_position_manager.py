"""
SmartPositionManager 单元测试

测试6大特性:
1. 信号确认
2. RSI 过滤
3. 最小持仓期
4. 移动止损
5. 渐进仓位
6. 分批建仓/平仓
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

from analysis.smart_position_manager import (
    SmartPositionManager,
    SmartPositionConfig,
    REGIME_PARAMS,
    DEFAULT_CONFIG,
)


def make_row(signal='HOLD', confidence=0.5, rsi=50.0, atr=50.0,
             close=3000.0, regime='SIDEWAYS'):
    """构造一行测试数据"""
    return {
        'fused_signal': signal,
        'fused_confidence': confidence,
        'rsi': rsi,
        'atr': atr,
        'close': close,
        'regime_label': regime,
    }


class TestSignalConfirmation:
    """测试信号确认特性"""

    def test_single_buy_not_confirmed(self):
        """单次 BUY 信号不应建仓 (confirm_days=2)"""
        config = SmartPositionConfig(confirm_days=2, entry_steps=1)
        mgr = SmartPositionManager(config)
        pos = mgr.step(make_row(signal='BUY'))
        assert pos == 0.0, f"Expected 0.0, got {pos}"

    def test_two_consecutive_buy_confirmed(self):
        """连续2次 BUY 应建仓"""
        config = SmartPositionConfig(confirm_days=2, entry_steps=1)
        mgr = SmartPositionManager(config)
        mgr.step(make_row(signal='BUY'))
        pos = mgr.step(make_row(signal='BUY'))
        assert pos > 0, f"Expected position > 0, got {pos}"

    def test_interrupted_signal_resets(self):
        """BUY 被 HOLD 中断后需要重新计数"""
        config = SmartPositionConfig(confirm_days=2, entry_steps=1)
        mgr = SmartPositionManager(config)
        mgr.step(make_row(signal='BUY'))
        mgr.step(make_row(signal='HOLD'))
        pos = mgr.step(make_row(signal='BUY'))
        assert pos == 0.0, f"Expected 0.0 after interruption, got {pos}"

    def test_confirm_days_1_immediate(self):
        """confirm_days=1 时立即执行"""
        config = SmartPositionConfig(confirm_days=1, entry_steps=1)
        mgr = SmartPositionManager(config)
        pos = mgr.step(make_row(signal='BUY'))
        assert pos > 0, f"Expected immediate entry, got {pos}"


class TestRSIFilter:
    """测试 RSI 超买超卖过滤"""

    def test_buy_suppressed_when_overbought(self):
        """RSI > overbought 时 BUY 被抑制"""
        config = SmartPositionConfig(
            confirm_days=1, rsi_overbought=75.0, entry_steps=1
        )
        mgr = SmartPositionManager(config)
        pos = mgr.step(make_row(signal='BUY', rsi=80.0))
        assert pos == 0.0, f"BUY should be suppressed at RSI=80, got {pos}"

    def test_buy_allowed_below_overbought(self):
        """RSI < overbought 时 BUY 正常执行"""
        config = SmartPositionConfig(
            confirm_days=1, rsi_overbought=75.0, entry_steps=1
        )
        mgr = SmartPositionManager(config)
        pos = mgr.step(make_row(signal='BUY', rsi=60.0))
        assert pos > 0, f"BUY should work at RSI=60, got {pos}"

    def test_sell_suppressed_when_oversold(self):
        """RSI < oversold 时 SELL 被抑制"""
        config = SmartPositionConfig(
            confirm_days=1, rsi_oversold=25.0, entry_steps=1,
            min_hold_days=0,
        )
        mgr = SmartPositionManager(config)
        # 先建仓
        mgr.step(make_row(signal='BUY', rsi=50.0))
        # 尝试卖出 (RSI=20, 被抑制)
        pos = mgr.step(make_row(signal='SELL', rsi=20.0))
        assert pos > 0, f"SELL should be suppressed at RSI=20, got {pos}"

    def test_rsi_filter_disabled(self):
        """RSI 过滤关闭时不影响信号"""
        config = SmartPositionConfig(
            confirm_days=1, rsi_filter_enabled=False, entry_steps=1
        )
        mgr = SmartPositionManager(config)
        pos = mgr.step(make_row(signal='BUY', rsi=90.0))
        assert pos > 0, f"BUY should work with filter disabled, got {pos}"


class TestMinHoldPeriod:
    """测试最小持仓期"""

    def test_sell_blocked_before_min_hold(self):
        """持仓天数不足时 SELL 被阻止"""
        config = SmartPositionConfig(
            confirm_days=1, min_hold_days=5, entry_steps=1
        )
        mgr = SmartPositionManager(config)
        # 建仓
        mgr.step(make_row(signal='BUY'))
        # 第2天就尝试卖出
        pos = mgr.step(make_row(signal='SELL'))
        assert pos > 0, f"SELL should be blocked at day 1, got {pos}"

    def test_sell_allowed_after_min_hold(self):
        """持仓天数足够后 SELL 生效"""
        config = SmartPositionConfig(
            confirm_days=1, min_hold_days=3, entry_steps=1, exit_steps=1
        )
        mgr = SmartPositionManager(config)
        # 建仓
        mgr.step(make_row(signal='BUY'))
        # 持有3天 (HOLD)
        for _ in range(3):
            mgr.step(make_row(signal='HOLD'))
        # 第4天卖出
        pos = mgr.step(make_row(signal='SELL'))
        assert pos == 0.0, f"SELL should work after min_hold, got {pos}"


class TestTrailingStop:
    """测试移动止损"""

    def test_stop_triggered_on_drawdown(self):
        """价格下跌超过阈值触发止损"""
        config = SmartPositionConfig(
            confirm_days=1, trailing_stop_atr_mult=2.0,
            trailing_stop_enabled=True, entry_steps=1,
            min_hold_days=0,
        )
        mgr = SmartPositionManager(config)
        # 建仓 close=3000
        mgr.step(make_row(signal='BUY', close=3000.0, atr=50.0))
        # 价格上涨到 3100 (更新 peak)
        mgr.step(make_row(signal='HOLD', close=3100.0, atr=50.0))
        # 价格下跌到 2900: drawdown = (3100-2900)/3100 = 6.5%
        # threshold = 50*2.0/2900 = 3.4%
        # 6.5% > 3.4% -> 触发止损
        pos = mgr.step(make_row(signal='HOLD', close=2900.0, atr=50.0))
        assert pos == 0.0, f"Stop should trigger, got {pos}"

    def test_no_stop_within_threshold(self):
        """价格小幅回调不触发止损"""
        config = SmartPositionConfig(
            confirm_days=1, trailing_stop_atr_mult=3.0,
            trailing_stop_enabled=True, entry_steps=1,
            min_hold_days=0,
        )
        mgr = SmartPositionManager(config)
        # 建仓 close=3000
        mgr.step(make_row(signal='BUY', close=3000.0, atr=50.0))
        # 小幅回调 close=2980: drawdown=0.67%, threshold=50*3/2980=5.0%
        pos = mgr.step(make_row(signal='HOLD', close=2980.0, atr=50.0))
        assert pos > 0, f"Stop should NOT trigger, got {pos}"

    def test_stop_bypasses_min_hold(self):
        """止损优先于最小持仓期"""
        config = SmartPositionConfig(
            confirm_days=1, trailing_stop_atr_mult=1.0,
            trailing_stop_enabled=True, entry_steps=1,
            min_hold_days=10,
        )
        mgr = SmartPositionManager(config)
        # 建仓
        mgr.step(make_row(signal='BUY', close=3000.0, atr=100.0))
        # 大跌: drawdown = (3000-2800)/3000 = 6.7%, threshold=100*1.0/2800=3.6%
        pos = mgr.step(make_row(signal='HOLD', close=2800.0, atr=100.0))
        assert pos == 0.0, f"Stop should bypass min_hold, got {pos}"


class TestGradualSizing:
    """测试渐进仓位"""

    def test_high_confidence_high_position(self):
        """高 confidence 映射到高仓位"""
        config = SmartPositionConfig(
            confirm_days=1, min_position=0.3, max_position=1.0, entry_steps=1
        )
        mgr = SmartPositionManager(config)
        pos = mgr.step(make_row(signal='BUY', confidence=1.0))
        assert abs(pos - 1.0) < 0.01, f"Expected ~1.0, got {pos}"

    def test_low_confidence_low_position(self):
        """低 confidence 映射到低仓位"""
        config = SmartPositionConfig(
            confirm_days=1, min_position=0.3, max_position=1.0, entry_steps=1
        )
        mgr = SmartPositionManager(config)
        pos = mgr.step(make_row(signal='BUY', confidence=0.0))
        assert abs(pos - 0.3) < 0.01, f"Expected ~0.3, got {pos}"

    def test_mid_confidence(self):
        """中等 confidence 映射到中等仓位"""
        config = SmartPositionConfig(
            confirm_days=1, min_position=0.2, max_position=0.8, entry_steps=1
        )
        mgr = SmartPositionManager(config)
        # confidence=0.5 -> 0.2 + 0.6*0.5 = 0.5
        pos = mgr.step(make_row(signal='BUY', confidence=0.5))
        assert abs(pos - 0.5) < 0.01, f"Expected ~0.5, got {pos}"


class TestBatchEntry:
    """测试分批建仓/平仓"""

    def test_two_step_entry(self):
        """2步建仓: 仓位分2步增加"""
        config = SmartPositionConfig(
            confirm_days=1, entry_steps=2, step_interval_days=1,
            min_position=0.5, max_position=0.5,  # 固定仓位方便测试
        )
        mgr = SmartPositionManager(config)
        # 第1步: 建仓 0.5/2 = 0.25
        pos1 = mgr.step(make_row(signal='BUY', confidence=1.0))
        assert abs(pos1 - 0.25) < 0.01, f"Step 1: expected ~0.25, got {pos1}"

        # 第2步: 等待 step_interval (1天) 后加仓到 0.5
        pos2 = mgr.step(make_row(signal='HOLD'))
        assert abs(pos2 - 0.5) < 0.01, f"Step 2: expected ~0.5, got {pos2}"

    def test_batch_exit(self):
        """分批平仓"""
        config = SmartPositionConfig(
            confirm_days=1, entry_steps=1, exit_steps=2,
            step_interval_days=1, min_hold_days=0,
            min_position=0.5, max_position=0.5,
        )
        mgr = SmartPositionManager(config)
        # 建仓
        mgr.step(make_row(signal='BUY', confidence=1.0))
        # 卖出信号
        pos1 = mgr.step(make_row(signal='SELL'))
        # 第1步减仓
        pos2 = mgr.step(make_row(signal='HOLD'))
        # 应该减少了
        assert pos2 < 0.5, f"Should have reduced position, got {pos2}"


class TestRegimeSwitching:
    """测试市场状态切换"""

    def test_bull_trend_fast_confirm(self):
        """BULL_TREND: confirm_days=1, 立即建仓"""
        mgr = SmartPositionManager()
        pos = mgr.step(make_row(signal='BUY', regime='BULL_TREND'))
        assert pos > 0, f"BULL_TREND should confirm in 1 day, got {pos}"

    def test_bear_trend_slow_confirm(self):
        """BEAR_TREND: confirm_days=2, 需要2天确认"""
        mgr = SmartPositionManager()
        pos = mgr.step(make_row(signal='BUY', regime='BEAR_TREND'))
        assert pos == 0.0, f"BEAR_TREND needs 2 days, 1st day should be 0, got {pos}"
        pos = mgr.step(make_row(signal='BUY', regime='BEAR_TREND'))
        assert pos > 0, f"BEAR_TREND 2nd day should confirm, got {pos}"

    def test_regime_params_exist(self):
        """所有6种状态都有参数配置"""
        expected_regimes = [
            'BULL_TREND', 'BULL_LATE', 'BEAR_TREND',
            'BEAR_LATE', 'SIDEWAYS', 'HIGH_VOL'
        ]
        for regime in expected_regimes:
            assert regime in REGIME_PARAMS, f"Missing REGIME_PARAMS for {regime}"
            params = REGIME_PARAMS[regime]
            assert isinstance(params, SmartPositionConfig)

    def test_bull_trend_higher_max_position(self):
        """BULL_TREND 最大仓位高于 BEAR_TREND"""
        bull = REGIME_PARAMS['BULL_TREND']
        bear = REGIME_PARAMS['BEAR_TREND']
        assert bull.max_position > bear.max_position


class TestStopLossPriority:
    """测试止损优先级"""

    def test_stop_cancels_pending_exit(self):
        """止损应取消分批平仓，立即清仓"""
        config = SmartPositionConfig(
            confirm_days=1, entry_steps=1, exit_steps=3,
            step_interval_days=1, min_hold_days=0,
            trailing_stop_atr_mult=1.0, trailing_stop_enabled=True,
            min_position=1.0, max_position=1.0,
        )
        mgr = SmartPositionManager(config)
        # 建仓
        mgr.step(make_row(signal='BUY', close=3000.0, atr=100.0))
        # SELL 触发分批平仓
        mgr.step(make_row(signal='SELL', close=3000.0, atr=100.0))
        # 价格暴跌触发止损
        pos = mgr.step(make_row(signal='HOLD', close=2800.0, atr=100.0))
        assert pos == 0.0, f"Stop should override batch exit, got {pos}"


class TestGeneratePositions:
    """测试 generate_positions 完整流程"""

    def test_basic_flow(self):
        """基本 DataFrame 处理流程"""
        df = pd.DataFrame({
            'trade_date': pd.date_range('2024-01-01', periods=10),
            'fused_signal': ['HOLD'] * 3 + ['BUY'] * 4 + ['SELL'] * 3,
            'fused_confidence': [0.5] * 10,
            'rsi': [50.0] * 10,
            'atr': [50.0] * 10,
            'close': [3000.0] * 10,
            'regime_label': ['SIDEWAYS'] * 10,
        })
        mgr = SmartPositionManager(SmartPositionConfig(
            confirm_days=1, entry_steps=1, min_hold_days=0, exit_steps=1
        ))
        positions = mgr.generate_positions(df)
        assert len(positions) == len(df)
        # T+1 延迟: 第0天 position 应为 0
        assert positions.iloc[0] == 0.0
        # 应有一些非零仓位
        assert (positions > 0).any()

    def test_t_plus_1_delay(self):
        """验证 T+1 延迟"""
        df = pd.DataFrame({
            'trade_date': pd.date_range('2024-01-01', periods=5),
            'fused_signal': ['BUY', 'BUY', 'HOLD', 'HOLD', 'HOLD'],
            'fused_confidence': [0.8] * 5,
            'rsi': [50.0] * 5,
            'atr': [50.0] * 5,
            'close': [3000.0] * 5,
            'regime_label': ['BULL_TREND'] * 5,  # confirm_days=1
        })
        mgr = SmartPositionManager()
        positions = mgr.generate_positions(df)
        # T=0 发出 BUY 决策，T=1 才有仓位
        assert positions.iloc[0] == 0.0
        assert positions.iloc[1] > 0, f"T+1 should have position, got {positions.iloc[1]}"


def run_all_tests():
    """运行所有测试"""
    test_classes = [
        TestSignalConfirmation,
        TestRSIFilter,
        TestMinHoldPeriod,
        TestTrailingStop,
        TestGradualSizing,
        TestBatchEntry,
        TestRegimeSwitching,
        TestStopLossPriority,
        TestGeneratePositions,
    ]

    total = 0
    passed = 0
    failed = 0
    errors = []

    for cls in test_classes:
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith('test_')]
        for method_name in methods:
            total += 1
            test_fn = getattr(instance, method_name)
            try:
                test_fn()
                passed += 1
                print(f"  [PASS] {cls.__name__}.{method_name}")
            except Exception as e:
                failed += 1
                errors.append((cls.__name__, method_name, str(e)))
                print(f"  [FAIL] {cls.__name__}.{method_name}: {e}")

    print(f"\n{'=' * 60}")
    print(f"  Total: {total}, Passed: {passed}, Failed: {failed}")
    print(f"{'=' * 60}")

    if errors:
        print("\nFailed tests:")
        for cls_name, method, err in errors:
            print(f"  {cls_name}.{method}: {err}")

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
