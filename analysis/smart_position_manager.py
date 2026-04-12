"""
V10 智能仓位管理模块

将二元仓位 (0/1) 转化为连续仓位 (0.0~1.0)，通过10大特性优化买卖时机：

V9 原有特性:
1. 信号确认: 连续N天同方向信号才执行
2. RSI超买超卖过滤: RSI>阈值抑制BUY, RSI<阈值抑制SELL
3. 最小持仓期: 入场后至少持有N天（止损除外）
4. 移动止损: 跟踪最高价，回撤超阈值立即清仓
5. 渐进仓位: 根据confidence映射仓位大小
6. 分批建仓/平仓: 多步进出，避免单点全仓

V10 新增特性:
7. Regime转换仓位保护: 市场状态降级时主动减仓
8. 技术背离预警: RSI+MACD背离时减仓30%
9. 成交量确认入场: BUY需量能配合
10. 动态仓位缩放: 持仓期间根据regime持续调整仓位

所有参数根据市场状态 (6种regime) 动态调整。

使用:
    manager = SmartPositionManager()
    positions = manager.generate_positions(df, signal_col='fused_signal')
"""

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd


# ==================== Regime 等级定义 ====================

REGIME_RANK: Dict[str, int] = {
    'BULL_TREND': 5,
    'BULL_LATE': 4,
    'BEAR_LATE': 3,   # 底部反转，正面信号
    'SIDEWAYS': 2,
    'HIGH_VOL': 1,
    'BEAR_TREND': 0,
}


@dataclass
class SmartPositionConfig:
    """智能仓位管理配置"""

    # 信号确认
    confirm_days: int = 1

    # RSI 过滤
    rsi_overbought: float = 75.0
    rsi_oversold: float = 25.0
    rsi_filter_enabled: bool = True

    # 最小持仓期
    min_hold_days: int = 3

    # 移动止损
    trailing_stop_atr_mult: float = 2.0
    trailing_stop_enabled: bool = True

    # 渐进仓位
    min_position: float = 0.4
    max_position: float = 1.0

    # 分批建仓/平仓
    entry_steps: int = 1
    exit_steps: int = 1
    step_interval_days: int = 1

    # V10: Regime转换保护
    regime_transition_enabled: bool = True

    # V10: 背离检测
    divergence_enabled: bool = True
    divergence_reduction: float = 0.7     # 看跌背离时仓位乘以此值
    divergence_cooldown_days: int = 5

    # V10: 成交量确认
    volume_confirm_enabled: bool = True
    volume_threshold: float = 1.0         # vol > threshold * vol_ma_10

    # V10: 动态仓位缩放
    dynamic_scaling_enabled: bool = True
    scale_speed_down: float = 0.15        # 每日缩仓速度
    scale_speed_up: float = 0.10          # 每日加仓速度


# 默认配置 (SIDEWAYS 参数)
DEFAULT_CONFIG = SmartPositionConfig()

# 6种市场状态的参数矩阵
# V10: 新增 regime_transition, divergence, volume_confirm, dynamic_scaling 参数
REGIME_PARAMS: Dict[str, SmartPositionConfig] = {
    'BULL_TREND': SmartPositionConfig(
        confirm_days=1,
        rsi_overbought=82.0,
        rsi_oversold=20.0,
        min_hold_days=3,
        trailing_stop_atr_mult=5.0,
        min_position=0.6,
        max_position=1.0,
        entry_steps=1,
        exit_steps=1,
        step_interval_days=1,
        # V10
        regime_transition_enabled=True,
        divergence_enabled=False,         # 强牛市不启用背离（误报多）
        divergence_reduction=0.85,
        divergence_cooldown_days=5,
        volume_confirm_enabled=False,     # 禁用：过滤有效入场
        volume_threshold=0.6,
        dynamic_scaling_enabled=False,    # 禁用：牛市不应缩仓
        scale_speed_down=0.05,
        scale_speed_up=0.15,
    ),
    'BULL_LATE': SmartPositionConfig(
        confirm_days=1,
        rsi_overbought=72.0,
        rsi_oversold=25.0,
        min_hold_days=3,
        trailing_stop_atr_mult=3.5,
        min_position=0.4,
        max_position=0.8,
        entry_steps=1,
        exit_steps=1,
        step_interval_days=1,
        # V10
        regime_transition_enabled=True,
        divergence_enabled=True,          # 末期启用背离检测
        divergence_reduction=0.85,
        divergence_cooldown_days=5,
        volume_confirm_enabled=False,     # 禁用
        volume_threshold=0.9,
        dynamic_scaling_enabled=False,    # 禁用
        scale_speed_down=0.08,
        scale_speed_up=0.08,
    ),
    'BEAR_TREND': SmartPositionConfig(
        confirm_days=2,
        rsi_overbought=75.0,
        rsi_oversold=22.0,
        min_hold_days=5,
        trailing_stop_atr_mult=3.0,
        min_position=0.3,
        max_position=0.6,
        entry_steps=1,
        exit_steps=1,
        step_interval_days=1,
        # V10
        regime_transition_enabled=True,
        divergence_enabled=True,
        divergence_reduction=0.85,
        divergence_cooldown_days=5,
        volume_confirm_enabled=False,     # 禁用
        volume_threshold=1.2,
        dynamic_scaling_enabled=False,    # 禁用
        scale_speed_down=0.12,
        scale_speed_up=0.0,
    ),
    'BEAR_LATE': SmartPositionConfig(
        confirm_days=1,
        rsi_overbought=80.0,
        rsi_oversold=18.0,
        min_hold_days=3,
        trailing_stop_atr_mult=4.0,
        min_position=0.5,
        max_position=0.9,
        entry_steps=1,
        exit_steps=1,
        step_interval_days=1,
        # V10
        regime_transition_enabled=True,
        divergence_enabled=True,
        divergence_reduction=0.85,
        divergence_cooldown_days=5,
        volume_confirm_enabled=False,     # 禁用
        volume_threshold=0.8,
        dynamic_scaling_enabled=False,    # 禁用
        scale_speed_down=0.06,
        scale_speed_up=0.10,
    ),
    'SIDEWAYS': SmartPositionConfig(
        confirm_days=1,
        rsi_overbought=75.0,
        rsi_oversold=25.0,
        min_hold_days=3,
        trailing_stop_atr_mult=4.0,
        min_position=0.4,
        max_position=1.0,
        entry_steps=1,
        exit_steps=1,
        step_interval_days=1,
        # V10
        regime_transition_enabled=True,
        divergence_enabled=True,
        divergence_reduction=0.85,
        divergence_cooldown_days=5,
        volume_confirm_enabled=False,     # 禁用
        volume_threshold=0.9,
        dynamic_scaling_enabled=False,    # 禁用
        scale_speed_down=0.06,
        scale_speed_up=0.06,
    ),
    'HIGH_VOL': SmartPositionConfig(
        confirm_days=2,
        rsi_overbought=72.0,
        rsi_oversold=28.0,
        min_hold_days=2,
        trailing_stop_atr_mult=4.0,
        min_position=0.3,
        max_position=0.6,
        entry_steps=1,
        exit_steps=1,
        step_interval_days=1,
        # V10
        regime_transition_enabled=True,
        divergence_enabled=True,
        divergence_reduction=0.85,
        divergence_cooldown_days=5,
        volume_confirm_enabled=False,     # 禁用
        volume_threshold=0.8,
        dynamic_scaling_enabled=False,    # 禁用
        scale_speed_down=0.10,
        scale_speed_up=0.0,
    ),
}


class SmartPositionManager:
    """
    V10 智能仓位管理器

    有状态类，每个指数维护一个实例。
    通过 step() 逐日处理，输出连续仓位 (0.0~1.0)。

    处理顺序:
        Phase 0:   获取 regime 参数
        Phase 0.5: Regime 转换仓位保护 (V10)
        Phase 1:   移动止损 (最高优先级)
        Phase 1.5: 技术背离预警 (V10)
        Phase 2:   分批步骤执行
        Phase 3:   RSI 过滤
        Phase 4:   信号确认
        Phase 4.5: 成交量确认入场 (V10)
        Phase 5:   最小持仓期
        Phase 6:   渐进仓位 + 分批建仓/平仓
        Phase 6.5: 动态仓位缩放 (V10)
    """

    def __init__(self, config: Optional[SmartPositionConfig] = None):
        self._custom_config = config  # None = 使用 REGIME_PARAMS
        self._default_config = config or DEFAULT_CONFIG
        self.reset()

    def reset(self):
        """重置所有状态"""
        self.signal_buffer: list = []
        self.current_position: float = 0.0
        self.days_held: int = 0
        self.peak_price: float = 0.0
        self.entry_price: float = 0.0
        self.pending_entry_steps: int = 0
        self.pending_exit_steps: int = 0
        self.days_since_last_step: int = 0
        self.target_full_position: float = 0.0
        # V10 新增状态
        self.prev_regime: str = 'SIDEWAYS'
        self.divergence_cooldown: int = 0
        self.divergence_boost: bool = False
        self._position_changed_this_step: bool = False

    def step(self, row_data: dict) -> float:
        """
        处理一天数据，返回目标仓位 (0.0~1.0)

        Args:
            row_data: {
                'fused_signal': str (BUY/SELL/HOLD),
                'fused_confidence': float (0~1),
                'rsi': float (0~100),
                'atr': float,
                'close': float,
                'regime_label': str,
                'vol': float,              (V10)
                'vol_ma_10': float,        (V10)
                'divergence_signal': str,  (V10, 'bearish'/'bullish'/None)
            }

        Returns:
            float: 目标仓位 0.0~1.0
        """
        raw_signal = str(row_data.get('fused_signal', 'HOLD'))
        confidence = float(row_data.get('fused_confidence', 0.5))
        rsi = float(row_data.get('rsi', 50.0))
        atr = float(row_data.get('atr', 0.0))
        close = float(row_data.get('close', 0.0))
        regime = str(row_data.get('regime_label', 'SIDEWAYS'))

        if close <= 0:
            return self.current_position

        self._position_changed_this_step = False

        # Phase 0: 获取当前 regime 参数
        if self._custom_config is not None:
            params = self._custom_config
        else:
            params = REGIME_PARAMS.get(regime, self._default_config)

        # Phase 0.5: Regime 转换仓位保护 (V10)
        if params.regime_transition_enabled and self.current_position > 0:
            phase05_result = self._handle_regime_transition(regime, params)
            if phase05_result is not None:
                self.prev_regime = regime
                return phase05_result

        # Phase 1: 移动止损 (最高优先级)
        if self.current_position > 0 and params.trailing_stop_enabled:
            self.peak_price = max(self.peak_price, close)
            if self.peak_price > 0:
                drawdown = (self.peak_price - close) / self.peak_price
                if atr > 0 and close > 0:
                    threshold = atr * params.trailing_stop_atr_mult / close
                else:
                    threshold = 0.08
                if drawdown > threshold:
                    self._reset_position_state()
                    self.prev_regime = regime
                    return 0.0

        # Phase 1.5: 技术背离预警 (V10)
        if params.divergence_enabled and self.current_position > 0:
            phase15_result = self._check_divergence(row_data, params)
            if phase15_result is not None:
                self.prev_regime = regime
                return phase15_result

        # 背离冷却递减
        if self.divergence_cooldown > 0:
            self.divergence_cooldown -= 1

        # Phase 2: 分批步骤执行
        phase2_result = self._execute_batch_steps(params, raw_signal, rsi, close)
        if phase2_result is not None:
            self.prev_regime = regime
            return phase2_result

        # 持仓天数递增
        if self.current_position > 0:
            self.days_held += 1

        # Phase 3: RSI 过滤
        filtered_signal = self._apply_rsi_filter(raw_signal, rsi, params)

        # Phase 4: 信号确认
        confirmed_signal = self._confirm_signal(filtered_signal, params)

        # Phase 4.5: 成交量确认入场 (V10)
        if params.volume_confirm_enabled and confirmed_signal == 'BUY':
            confirmed_signal = self._check_volume_confirmation(
                confirmed_signal, row_data, params)

        # Phase 5: 最小持仓期
        if confirmed_signal == 'SELL' and self.current_position > 0:
            if self.days_held < params.min_hold_days:
                confirmed_signal = 'HOLD'

        # 看涨背离 boost: 提升下次 BUY 信号的 confidence
        if self.divergence_boost and confirmed_signal == 'BUY':
            confidence = min(1.0, confidence + 0.15)
            self.divergence_boost = False

        # Phase 6: 渐进仓位 + 分批建仓/平仓
        self._apply_position_change(confirmed_signal, confidence, close, params)

        # Phase 6.5: 动态仓位缩放 (V10)
        if (params.dynamic_scaling_enabled
                and self.current_position > 0.001
                and not self._position_changed_this_step):
            self._apply_dynamic_scaling(confidence, regime, params)

        self.prev_regime = regime
        return self.current_position

    def generate_positions(self, df: pd.DataFrame,
                           signal_col: str = 'fused_signal') -> pd.Series:
        """
        对整个 DataFrame 生成仓位序列 (含 T+1 延迟)

        V10: 预计算背离信号，新增 vol/vol_ma_10 传递
        """
        self.reset()

        # V10: 预计算背离信号
        divergence_signals = self._detect_divergences(df)

        positions = pd.Series(0.0, index=df.index)

        for i in range(len(df)):
            row = df.iloc[i]
            row_data = {
                'fused_signal': row.get(signal_col, 'HOLD'),
                'fused_confidence': row.get('fused_confidence',
                                            _calc_confidence(row)),
                'rsi': _safe_float(row.get('rsi', 50.0)),
                'atr': _safe_float(row.get('atr', 0.0)),
                'close': _safe_float(row.get('close', 0.0)),
                'regime_label': row.get('regime_label', 'SIDEWAYS'),
                # V10 新增
                'vol': _safe_float(row.get('vol', 0.0)),
                'vol_ma_10': _safe_float(row.get('vol_ma_10', 0.0)),
                'divergence_signal': divergence_signals.iloc[i],
            }
            positions.iloc[i] = self.step(row_data)

        # T+1 延迟: T日决策 -> T+1日执行
        return positions.shift(1).fillna(0.0)

    # ==================== V10 新增 Phase 方法 ====================

    def _handle_regime_transition(self, regime: str,
                                  params: SmartPositionConfig) -> Optional[float]:
        """
        Phase 0.5: Regime 转换仓位保护

        当市场状态降级时，主动减仓。升级时不强制加仓（快速防守、谨慎进攻）。

        Returns:
            float if position was reduced (return early),
            None if no action taken
        """
        if regime == self.prev_regime:
            return None

        prev_rank = REGIME_RANK.get(self.prev_regime, 2)
        curr_rank = REGIME_RANK.get(regime, 2)

        if curr_rank >= prev_rank:
            # 升级或平级：不强制加仓
            return None

        # 降级处理 - 仅对严重降级做保护
        downgrade_levels = prev_rank - curr_rank

        if regime == 'BEAR_TREND':
            # 进入 BEAR_TREND: 缩到 min(当前, 0.6)
            new_pos = min(self.current_position, 0.6)
        elif downgrade_levels >= 3:
            # 降级3+级: 缩减到新 regime 的 max_position * 0.9
            new_pos = min(self.current_position, params.max_position * 0.9)
        else:
            # 降级1-2级: 不做强制减仓，让止损机制自然保护
            return None

        if new_pos < self.current_position:
            self.current_position = new_pos
            if self.current_position <= 0.001:
                self._reset_position_state()
                return 0.0
            return self.current_position

        return None

    def _check_divergence(self, row_data: dict,
                          params: SmartPositionConfig) -> Optional[float]:
        """
        Phase 1.5: 技术背离预警

        看跌背离: 仓位 > 0.5 时减仓 30%
        看涨背离: 设置 boost 标记，下次 BUY 时提升 confidence

        Returns:
            float if position was reduced (return early),
            None if no action taken
        """
        div_signal = row_data.get('divergence_signal')

        if div_signal == 'bearish' and self.divergence_cooldown <= 0:
            if self.current_position > 0.6:
                self.current_position *= params.divergence_reduction
                self.divergence_cooldown = params.divergence_cooldown_days
                return self.current_position

        elif div_signal == 'bullish' and self.divergence_cooldown <= 0:
            if self.current_position < 0.5:
                self.divergence_boost = True

        return None

    def _check_volume_confirmation(self, signal: str, row_data: dict,
                                   params: SmartPositionConfig) -> str:
        """
        Phase 4.5: 成交量确认入场

        仅对 BUY 信号生效。vol > threshold * vol_ma_10 才确认。
        """
        if signal != 'BUY':
            return signal

        vol = float(row_data.get('vol', 0.0))
        vol_ma_10 = float(row_data.get('vol_ma_10', 0.0))

        if vol_ma_10 <= 0:
            # 无成交量数据时不过滤
            return signal

        if vol >= params.volume_threshold * vol_ma_10:
            return 'BUY'
        else:
            return 'HOLD'

    def _apply_dynamic_scaling(self, confidence: float, regime: str,
                               params: SmartPositionConfig):
        """
        Phase 6.5: 动态仓位缩放

        持仓期间根据当前 regime 参数持续调整仓位大小。
        bearish regime 禁止加仓，只能缩仓。
        """
        ideal = self._map_confidence_to_position(confidence, params)

        if ideal < self.current_position:
            # 缩仓
            speed = params.scale_speed_down
            self.current_position += speed * (ideal - self.current_position)
        elif ideal > self.current_position:
            # 加仓（bearish regime 禁止）
            if params.scale_speed_up > 0:
                speed = params.scale_speed_up
                self.current_position += speed * (ideal - self.current_position)

        # 应用 regime 上限
        self.current_position = min(self.current_position, params.max_position)
        self.current_position = max(self.current_position, 0.0)

    @staticmethod
    def _detect_divergences(df: pd.DataFrame, lookback: int = 20) -> pd.Series:
        """
        预计算技术背离信号 (向量化)

        看跌背离: 价格创近期新高，但 RSI 和 MACD_histogram 均未创新高
        看涨背离: 价格创近期新低，但 RSI 和 MACD_histogram 均未创新低

        Returns:
            pd.Series: 'bearish' / 'bullish' / None
        """
        result = pd.Series(None, index=df.index, dtype=object)

        close = pd.to_numeric(df.get('close'), errors='coerce')
        rsi = pd.to_numeric(df.get('rsi'), errors='coerce')
        macd_hist = pd.to_numeric(
            df.get('macd_histogram', df.get('macd_hist')), errors='coerce')

        if close is None or rsi is None or macd_hist is None:
            return result

        if close.isna().all() or rsi.isna().all() or macd_hist.isna().all():
            return result

        # 滚动最高/最低价 (不含当日，用 shift(1))
        roll_max_close = close.shift(1).rolling(window=lookback, min_periods=5).max()
        roll_min_close = close.shift(1).rolling(window=lookback, min_periods=5).min()
        roll_max_rsi = rsi.shift(1).rolling(window=lookback, min_periods=5).max()
        roll_min_rsi = rsi.shift(1).rolling(window=lookback, min_periods=5).min()
        roll_max_macd = macd_hist.shift(1).rolling(window=lookback, min_periods=5).max()
        roll_min_macd = macd_hist.shift(1).rolling(window=lookback, min_periods=5).min()

        # 看跌背离: 价格创新高但 RSI 和 MACD 均未创新高
        bearish = (
            (close > roll_max_close) &
            (rsi < roll_max_rsi) &
            (macd_hist < roll_max_macd)
        )

        # 看涨背离: 价格创新低但 RSI 和 MACD 均未创新低
        bullish = (
            (close < roll_min_close) &
            (rsi > roll_min_rsi) &
            (macd_hist > roll_min_macd)
        )

        result[bearish.fillna(False)] = 'bearish'
        result[bullish.fillna(False)] = 'bullish'

        return result

    # ==================== V9 原有内部方法 ====================

    def _reset_position_state(self):
        """止损/完全平仓时重置仓位相关状态"""
        self.current_position = 0.0
        self.days_held = 0
        self.peak_price = 0.0
        self.entry_price = 0.0
        self.pending_entry_steps = 0
        self.pending_exit_steps = 0
        self.days_since_last_step = 0
        self.target_full_position = 0.0

    def _execute_batch_steps(self, params: SmartPositionConfig,
                             raw_signal: str, rsi: float,
                             close: float) -> Optional[float]:
        """
        Phase 2: 执行挂起的分批步骤

        Returns:
            float if batch step was executed and should return early,
            None if no pending steps or conflicting signal detected
        """
        if self.pending_entry_steps <= 0 and self.pending_exit_steps <= 0:
            return None

        self.days_since_last_step += 1

        # 持仓天数递增
        if self.current_position > 0:
            self.days_held += 1

        # 检测信号冲突: 先做快速RSI过滤+确认
        filtered = self._apply_rsi_filter(raw_signal, rsi, params)
        quick_confirmed = self._peek_confirm(filtered, params)

        if self.pending_entry_steps > 0:
            if quick_confirmed == 'SELL':
                self.pending_entry_steps = 0
                self.pending_exit_steps = params.exit_steps
                self.days_since_last_step = 0
                return None

            if self.days_since_last_step >= params.step_interval_days:
                step_size = self.target_full_position / params.entry_steps
                self.current_position = min(
                    self.current_position + step_size,
                    self.target_full_position
                )
                self.pending_entry_steps -= 1
                self.days_since_last_step = 0

            return self.current_position

        if self.pending_exit_steps > 0:
            if quick_confirmed == 'BUY':
                self.pending_exit_steps = 0
                return None

            if self.days_since_last_step >= params.step_interval_days:
                remaining = self.pending_exit_steps
                step_size = self.current_position / remaining
                self.current_position = max(
                    self.current_position - step_size, 0.0
                )
                self.pending_exit_steps -= 1
                self.days_since_last_step = 0

                if self.current_position <= 0.001:
                    self._reset_position_state()

            return self.current_position

        return None

    def _apply_rsi_filter(self, signal: str, rsi: float,
                          params: SmartPositionConfig) -> str:
        """Phase 3: RSI 超买超卖过滤"""
        if not params.rsi_filter_enabled:
            return signal
        if signal == 'BUY' and rsi > params.rsi_overbought:
            return 'HOLD'
        if signal == 'SELL' and rsi < params.rsi_oversold:
            return 'HOLD'
        return signal

    def _confirm_signal(self, signal: str,
                        params: SmartPositionConfig) -> str:
        """Phase 4: 信号确认 (N天连续同方向)"""
        self.signal_buffer.append(signal)
        max_len = max(params.confirm_days, 1)
        if len(self.signal_buffer) > max_len:
            self.signal_buffer = self.signal_buffer[-max_len:]

        if len(self.signal_buffer) < params.confirm_days:
            return 'HOLD'

        recent = self.signal_buffer[-params.confirm_days:]
        if all(s == 'BUY' for s in recent):
            return 'BUY'
        if all(s == 'SELL' for s in recent):
            return 'SELL'
        return 'HOLD'

    def _peek_confirm(self, signal: str,
                      params: SmartPositionConfig) -> str:
        """快速检查信号确认 (不修改 buffer)"""
        temp_buffer = self.signal_buffer + [signal]
        max_len = max(params.confirm_days, 1)
        if len(temp_buffer) > max_len:
            temp_buffer = temp_buffer[-max_len:]

        if len(temp_buffer) < params.confirm_days:
            return 'HOLD'

        recent = temp_buffer[-params.confirm_days:]
        if all(s == 'BUY' for s in recent):
            return 'BUY'
        if all(s == 'SELL' for s in recent):
            return 'SELL'
        return 'HOLD'

    def _apply_position_change(self, confirmed_signal: str,
                               confidence: float, close: float,
                               params: SmartPositionConfig):
        """Phase 6: 渐进仓位 + 分批建仓/平仓"""
        if confirmed_signal == 'BUY' and self.current_position <= 0.001:
            target = self._map_confidence_to_position(confidence, params)
            self.target_full_position = target

            if params.entry_steps <= 1:
                self.current_position = target
                self.pending_entry_steps = 0
            else:
                first_step = target / params.entry_steps
                self.current_position = first_step
                self.pending_entry_steps = params.entry_steps - 1
                self.days_since_last_step = 0

            self.entry_price = close
            self.peak_price = close
            self.days_held = 0
            self._position_changed_this_step = True

        elif confirmed_signal == 'BUY' and self.current_position > 0.001:
            new_target = self._map_confidence_to_position(confidence, params)
            if new_target > self.target_full_position:
                diff = new_target - self.current_position
                if diff > 0.05:
                    self.target_full_position = new_target
                    self.pending_entry_steps = 1
                    self.days_since_last_step = 0
                    self._position_changed_this_step = True

        elif confirmed_signal == 'SELL' and self.current_position > 0.001:
            if params.exit_steps <= 1:
                self._reset_position_state()
            else:
                self.pending_exit_steps = params.exit_steps
                self.days_since_last_step = 0
            self._position_changed_this_step = True

    @staticmethod
    def _map_confidence_to_position(confidence: float,
                                    params: SmartPositionConfig) -> float:
        """将 confidence (0~1) 映射到仓位 (min_position~max_position)"""
        conf = max(0.0, min(1.0, confidence))
        return params.min_position + (params.max_position - params.min_position) * conf

    @staticmethod
    def get_regime_params(regime_label: str) -> SmartPositionConfig:
        """获取指定市场状态的仓位参数"""
        return REGIME_PARAMS.get(regime_label, DEFAULT_CONFIG)


# ==================== 工具函数 ====================

def _safe_float(val, default: float = 0.0) -> float:
    """安全转换为 float"""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _calc_confidence(row) -> float:
    """从 row 计算 confidence (回退方案)"""
    if 'fused_confidence' in row.index:
        val = row['fused_confidence']
        if val is not None and not (isinstance(val, float) and np.isnan(val)):
            return float(val)
    for col in ['fused_score', 'factor_score']:
        if col in row.index:
            score = _safe_float(row[col], 50.0)
            return abs(score - 50.0) / 50.0
    return 0.5
