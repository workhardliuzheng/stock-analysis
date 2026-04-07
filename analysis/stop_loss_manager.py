#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
止损管理模块

功能:
1. 监控持仓盈亏
2. 触发止损条件
3. 生成止损信号
"""

import sys
sys.path.insert(0, r'E:\pycharm\stock-analysis')

from datetime import datetime
import pandas as pd


class StopLossManager:
    """
    止损管理器
    
    支持多种止损策略:
    1. 固定止损: 亏损达到X%时止损
    2. 追踪止损: 价格从最高点回撤X%时止损
    3. 时间止损: 持仓超过N天未盈利时止损
    4. 动态止损: 根据ATR动态调整止损位
    """
    
    def __init__(self, 
                 fixed_stop_loss: float = -10.0,  # 固定止损百分比
                 trailing_stop_loss: float = -8.0,  # 追踪止损百分比
                 time_stop_days: int = 10,  # 时间止损天数
                 atr_multiplier: float = 1.5,  # ATR止损倍数
                 enabled: bool = True):
        """
        Args:
            fixed_stop_loss: 固定止损百分比 (负数)
            trailing_stop_loss: 追踪止损百分比 (负数)
            time_stop_days: 时间止损天数
            atr_multiplier: ATR止损倍数
            enabled: 是否启用止损
        """
        self.fixed_stop_loss = fixed_stop_loss
        self.trailing_stop_loss = trailing_stop_loss
        self.time_stop_days = time_stop_days
        self.atr_multiplier = atr_multiplier
        self.enabled = enabled
        
        # 持仓跟踪
        self.holdings = {}  # code -> {'entry_price': float, 'entry_date': datetime, 'max_price': float}
    
    def update_position(self, code: str, price: float, trade_date: str):
        """更新持仓"""
        self.holdings[code] = {
            'entry_price': price,
            'entry_date': datetime.strptime(trade_date, '%Y%m%d'),
            'max_price': price,
        }
    
    def check_stop_loss(self, code: str, current_price: float, trade_date: str, 
                       df_row: pd.Series = None) -> tuple:
        """
        检查是否触发止损
        
        Args:
            code: 指数代码
            current_price: 当前价格
            trade_date: 交易日期 (支持多种格式)
            df_row: DataFrame 行数据（用于ATR止损）
        
        Returns:
            (triggered: bool, reason: str)
        """
        if not self.enabled:
            return False, ""
        
        if code not in self.holdings:
            return False, ""
        
        holding = self.holdings[code]
        
        # 支持多种日期格式 - 提取纯数字
        if isinstance(trade_date, (int, float)):
            date_str = str(int(trade_date))
        else:
            date_str = str(trade_date)
        
        # 移除非数字字符，只保留数字
        date_str = ''.join(c for c in date_str if c.isdigit())
        
        # 确保至少8位数字
        if len(date_str) >= 8:
            date_str = date_str[:8]  # 取前8位 YYYYMMDD
            try:
                current_date = datetime.strptime(date_str, '%Y%m%d')
            except ValueError:
                current_date = datetime.now()
        else:
            current_date = datetime.now()
        
        # 计算收益
        profit_pct = (current_price - holding['entry_price']) / holding['entry_price'] * 100
        
        # 1. 固定止损
        if profit_pct <= self.fixed_stop_loss:
            return True, f"固定止损触发: 亏损 {profit_pct:.2f}% <= {self.fixed_stop_loss:.2f}%"
        
        # 2. 追踪止损
        if current_price > holding['max_price']:
            holding['max_price'] = current_price
        
        pullback = (current_price - holding['max_price']) / holding['max_price'] * 100
        if pullback <= self.trailing_stop_loss:
            return True, f"追踪止损触发: 从最高点回撤 {pullback:.2f}% <= {self.trailing_stop_loss:.2f}%"
        
        # 3. 时间止损
        entry_date = holding['entry_date']
        holding_days = (current_date - entry_date).days
        if holding_days >= self.time_stop_days and profit_pct <= 0:
            return True, f"时间止损触发: 持仓 {holding_days} 天未盈利"
        
        # 4. 动态止损 (基于ATR)
        if df_row is not None and 'atr' in df_row:
            atr = df_row['atr']
            stop_price = holding['entry_price'] * (1 + self.fixed_stop_loss / 100 - atr * self.atr_multiplier / 100)
            if current_price <= stop_price:
                return True, f"动态止损触发: 价格 {current_price:.2f} <= 止损价 {stop_price:.2f}"
        
        return False, ""
    
    def remove_position(self, code: str):
        """移除持仓"""
        if code in self.holdings:
            del self.holdings[code]
    
    def get_all_positions(self) -> dict:
        """获取所有持仓"""
        return self.holdings.copy()


def apply_stop_signals(df: pd.DataFrame, stop_loss_manager: StopLossManager) -> pd.DataFrame:
    """
    应用止损信号
    
    Args:
        df: DataFrame (必须包含('close', 'trade_date', 'position')列)
        stop_loss_manager: 止损管理器
    
    Returns:
        pd.DataFrame: 新增 stop_signal 列
    """
    result = df.copy()
    result['stop_signal'] = 'HOLD'
    
    for i in range(len(result)):
        row = result.iloc[i]
        code = row.get('ts_code', 'UNKNOWN')
        current_price = row.get('close', 0)
        trade_date = row.get('trade_date', datetime.now().strftime('%Y%m%d'))
        position = row.get('position', 0)
        
        # 兼容多种日期格式
        if isinstance(trade_date, str):
            if '-' in trade_date:
                # '2021-04-01' -> '20210401'
                date_str = trade_date.replace('-', '')
            else:
                date_str = trade_date[:8] if len(trade_date) >= 8 else trade_date
        elif isinstance(trade_date, (int, float)):
            date_str = str(int(trade_date))[:8]
        else:
            date_str = str(trade_date)[:8]
        
        # 如果是买入信号，更新持仓
        if position == 1:
            stop_loss_manager.update_position(code, current_price, date_str)
        
        # 检查止损
        triggered, reason = stop_loss_manager.check_stop_loss(code, current_price, date_str, row)
        
        if triggered:
            result.loc[i, 'stop_signal'] = 'SELL'
            print(f"  [STOP LOSS] {code}: {reason}")
        
        # 如果平仓，移除持仓
        if position == 0 and code in stop_loss_manager.get_all_positions():
            stop_loss_manager.remove_position(code)
    
    return result


if __name__ == "__main__":
    # 测试
    print("[OK] 止损管理器测试")
    
    manager = StopLossManager(fixed_stop_loss=-10.0, trailing_stop_loss=-8.0)
    
    # 模拟持仓
    manager.update_position('TEST001', 100, '20260401')
    print(f"持仓: {manager.get_all_positions()}")
    
    # 测试固定止损
    triggered, reason = manager.check_stop_loss('TEST001', 85, '20260410')
    print(f"固定止损测试: {triggered} - {reason}")
    
    # 测试追踪止损
    manager.update_position('TEST002', 100, '20260401')
    triggered, reason = manager.check_stop_loss('TEST002', 110, '20260410')  # 上涨到110
    print(f"追踪止损测试 (上涨): {triggered} - {reason}")
    
    triggered, reason = manager.check_stop_loss('TEST002', 98, '20260411')  # 回撤到98
    print(f"追踪止损测试 (回撤): {triggered} - {reason}")
