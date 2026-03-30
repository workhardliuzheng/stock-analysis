"""
多指数回测器

支持多指数分散持仓的组合回测，计算组合收益率和绩效指标。
整合仓位管理器，实现动态仓位分配和风险控制。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime

from analysis.position_manager import PositionManager, PositionConfig
from analysis.advanced_position_manager import AdvancedPositionManager, AdvancedPositionConfig
from analysis.backtester import Backtester


class MultiIndexBacktester:
    """
    多指数组合回测器
    
    功能:
    1. 同时回测多个指数
    2. 动态仓位分配（基于预测收益和风险）
    3. 风险控制（单指数上限、总仓位上限）
    4. 组合总收益率计算
    
    示例:
        # 初始化
        mib = MultiIndexBacktester(
            initial_capital=100000,
            commission_rate=0.00006,
            advanced_config=AdvancedPositionConfig()
        )
        
        # 运行回测
        result = mib.run(
            df_list=[df1, df2, df3],
            signal_columns=['final_signal', 'final_signal', 'final_signal'],
            position_config=AdvancedPositionConfig()
        )
        
        # 查看结果
        print(f"组合总收益: {result['total_return']:.1f}%")
        print(f"组合年化: {result['annualized_return']:.1f}%")
    """
    
    def __init__(self,
                 initial_capital: float = 100000,
                 commission_rate: float = 0.00006,
                 position_manager: PositionManager = None,
                 advanced_config: AdvancedPositionConfig = None,
                 execution_timing: str = 'open'):
        """
        Args:
            initial_capital: 初始资金
            commission_rate: 单边佣金率
            position_manager: 仓位管理器 (PositionManager or AdvancedPositionManager)
            advanced_config: 高级仓位配置 (AdvancedPositionConfig)
            execution_timing: 执行时机 'open'/'close'
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.position_manager = position_manager or PositionManager()
        self.execution_timing = execution_timing
        self.index_backtesters = {}  # 每个指数的单指数回测器
    
    def run(self,
            df_list: List[pd.DataFrame],
            code_list: List[str],
            name_list: List[str],
            signal_columns: List[str] = None,
            use_ml_signals: bool = True,
            position_config: PositionConfig = None,
            use_market_timing: bool = True,
            market_timing_index: str = '000300.SH') -> dict:
        """
        运行多指数回测
        
        Args:
            df_list: 各指数的DataFrame列表
            code_list: 各指数代码列表
            name_list: 各指数名称列表
            signal_columns: 各指数的信号列名（默认为['final_signal'] * n）
            use_ml_signals: 是否使用 ml_probability 作为仓位依据
            position_config: 仓位配置 (PositionConfig or AdvancedPositionConfig)
            use_market_timing: 是否启用市场择时（沪深300>MA200才开仓）
            market_timing_index: 用于市场择时的指数代码（默认沪深300）
        
        Returns:
            dict: 组合回测结果
        """
        if len(df_list) != len(code_list) or len(df_list) != len(name_list):
            return {'error': 'df_list, code_list, name_list 长度必须一致'}
        
        if signal_columns is None:
            signal_columns = ['final_signal'] * len(df_list)
        
        # 根据配置类型选择仓位管理器
        if isinstance(position_config, AdvancedPositionConfig):
            self.position_manager = AdvancedPositionManager(position_config)
        elif position_config:
            self.position_manager.config = position_config
        
        # 初始化
        num_indices = len(df_list)
        n_days = min(len(df) for df in df_list)
        
        # 日期对齐
        dates = None
        for df in df_list:
            if dates is None:
                dates = df['trade_date'].tolist()
            else:
                dates = [d for d in dates if d in df['trade_date'].tolist()]
        
        # 初始化组合账户
        cash = self.initial_capital
        positions = {}  # {code: shares}
        daily_values = {}  # {date: total_value}
        daily_positions = []  # 记录每日仓位
        
        # 单指数回测器初始化
        for i, (df, code, name, sig_col) in enumerate(zip(df_list, code_list, name_list, signal_columns)):
            # 确保需要的列存在
            required_cols = ['open', 'close', 'pct_chg']
            for col in required_cols:
                if col not in df.columns:
                    return {'error': f'{name}: 缺少列 {col}'}
            
            # 单指数回测器
            bt = Backtester(
                initial_capital=self.initial_capital,
                commission_rate=self.commission_rate,
                execution_timing=self.execution_timing
            )
            self.index_backtesters[code] = bt
        
        # 批量计算各指数的 ML 概率（如果需要）
        index_signals_list = []
        for i, (df, code) in enumerate(zip(df_list, code_list)):
            signals = self._extract_index_signals(df, code, use_ml_signals, signal_columns[i])
            index_signals_list.append(signals)
        
        # 日型循环
        for day_idx in range(n_days):
            current_date = dates[day_idx]
            
            # 市场择时检查（使用沪深300的MA200）
            market_timing_ok = True
            market_timing_value = 1.0  # 默认正常市场
            if use_market_timing and market_timing_index in code_list:
                market_idx = code_list.index(market_timing_index)
                market_df = df_list[market_idx]
                if day_idx < len(market_df) and day_idx >= 200:
                    # 检查当日收盘价是否高于MA200
                    current_close = market_df.iloc[day_idx]['close']
                    ma200 = market_df.iloc[day_idx].get('ma200', 0)
                    if ma200 > 0 and current_close < ma200:
                        market_timing_ok = False
                        market_timing_value = 0.7  # 保守市场
                        print(f"  市场择时: {current_date} 沪深300 < MA200，降低仓位至70%")
            
            # 收集当日信号（使用当天早盘的信号）
            current_signals = {}
            # 收集当前价格（用于高级仓位管理器）
            current_prices = {}
            for i, (code, signals) in enumerate(zip(code_list, index_signals_list)):
                if day_idx < len(signals):
                    signal_data = signals[day_idx].copy()
                    current_prices[code] = df_list[i].iloc[day_idx]['close']  # 收集当前价格
                    # 添加市场择时信号
                    signal_data['market_timing'] = market_timing_value
                    # 如果市场择时不满足，强制调低信号强度
                    if not market_timing_ok:
                        signal_data['predicted_return'] *= market_timing_value
                        if signal_data['signal'] == 'BUY':
                            signal_data['confidence'] *= market_timing_value
                    current_signals[code] = signal_data
            
            # 仓位管理（支持 PositionManager 和 AdvancedPositionManager）
            # 先计算组合价值（用于高级仓位管理器）
            total_value = cash
            for code, shares in positions.items():
                df = df_list[code_list.index(code)]
                close_price = df.iloc[day_idx]['close']
                total_value += shares * close_price
            
            if hasattr(self.position_manager, 'calculate_positions_v6'):
                # 使用 AdvancedPositionManager 的新方法
                new_positions = self.position_manager.calculate_positions_v6(
                    current_signals,
                    cash_available=1.0,
                    portfolio_value=total_value,
                    current_prices=current_prices
                )
            else:
                # 使用传统 PositionManager 方法
                new_positions = self.position_manager.calculate_positions(
                    current_signals,
                    cash_available=1.0
                )
            
            # 调仓
            if day_idx > 0:  # 第一天不调仓（初始状态）
                cash, positions = self._rebalance(
                    cash, positions, new_positions, df_list, code_list, day_idx
                )
            
            # 计算组合价值
            total_value = cash
            for code, shares in positions.items():
                df = df_list[code_list.index(code)]
                close_price = df.iloc[day_idx]['close']
                total_value += shares * close_price
            
            daily_values[current_date] = total_value
            
            # 记录每日仓位
            daily_positions.append({
                'date': current_date,
                'positions': new_positions,
                'cash': cash,
                'total_value': total_value
            })
        
        # 计算组合回报率
        dates_sorted = sorted(daily_values.keys())
        values = [daily_values[d] for d in dates_sorted]
        
        # 计算每日回报
        daily_returns = []
        for i in range(1, len(values)):
            ret = (values[i] - values[i-1]) / values[i-1]
            daily_returns.append(ret)
        
        # 计算组合绩效
        total_return = (values[-1] - self.initial_capital) / self.initial_capital
        annualized_return = self._annualized(total_return, len(dates))
        max_drawdown = self._max_drawdown_from_values(values)
        sharpe_ratio = self._sharpe(daily_returns)
        
        # 交易统计
        total_commission = 0.0
        
        # 简单的指数回测对比（不重新运行，仅提取结果）
        # TODO: 完整实现各指数单独回测
        
        return {
            'total_return': round(total_return * 100, 2),
            'annualized_return': round(annualized_return * 100, 2),
            'max_drawdown': round(max_drawdown * 100, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'total_days': len(dates),
            'initial_capital': self.initial_capital,
            'final_value': round(values[-1], 2),
            'daily_positions': daily_positions,
            'index_results': {},  # 暂不返回
            'comparison': self._create_comparison_report(
                values, dates, daily_returns, self.initial_capital
            )
        }
    
    def _extract_index_signals(self, df: pd.DataFrame, code: str, 
                               use_ml_signals: bool, signal_col: str) -> List[dict]:
        """
        从DataFrame提取每日信号数据
        
        Returns:
            List[dict]: 每日信号 [{'date': ..., 'signal': ..., 'confidence': ..., ...}, ...]
        """
        signals = []
        for idx, row in df.iterrows():
            signal = row.get(signal_col, 'HOLD')
            
            # 信号强度（置信度）
            confidence = 0.0
            if use_ml_signals and 'ml_probability' in df.columns:
                # 使用 ML 概率作为置信度
                prob = row['ml_probability']
                confidence = abs(prob - 0.5) * 2  # 转换为 [0, 1] 的置信度
            
            # 预测收益
            predicted_return = 0.0
            if 'ml_predicted_return' in df.columns:
                predicted_return = row['ml_predicted_return']
            
            # 波动率（使用最近20日标准差）
            volatility = 0.02  # 默认值
            if 'pct_chg' in df.columns:
                recent_returns = df['pct_chg'].tail(20)
                if len(recent_returns) >= 10:
                    volatility = recent_returns.std()
            
            signals.append({
                'date': row.get('trade_date'),
                'signal': signal,
                'confidence': confidence,
                'predicted_return': predicted_return,
                'volatility': volatility
            })
        
        return signals
    
    def _rebalance(self, cash: float, positions: dict,
                   new_positions: dict,
                   df_list: List[pd.DataFrame],
                   code_list: List[str],
                   day_idx: int) -> tuple:
        """
        调仓
        
        Returns:
            (new_cash, new_positions)
        """
        # 清空现有仓位
        current_prices = {}
        for code, shares in positions.items():
            df = df_list[code_list.index(code)]
            close_price = df.iloc[day_idx]['close']
            current_prices[code] = close_price
            cash += shares * close_price
        
        positions = {}
        
        # 建立新仓位
        for code, target_weight in new_positions.items():
            if target_weight <= 0:
                continue
            
            df = df_list[code_list.index(code)]
            close_price = df.iloc[day_idx]['close']
            
            # 计算投资金额
            investment = cash * target_weight
            
            # 计算可买股数
            shares = int(investment / close_price)
            
            if shares > 0:
                cost = shares * close_price
                # 佣金（单边）
                commission = cost * self.commission_rate
                cost += commission
                
                if cost <= cash:
                    cash -= cost
                    positions[code] = shares
        
        return cash, positions
    
    def _get_index_results(self, df_list: List[pd.DataFrame],
                          code_list: List[str],
                          name_list: List[str],
                          signal_columns: List[str]) -> dict:
        """获取各指数的单指数回测结果"""
        results = {}
        
        for i, (df, code, name, sig_col) in enumerate(zip(df_list, code_list, name_list, signal_columns)):
            bt = self.index_backtesters.get(code)
            if bt:
                # 运行单指数回测
                result = bt.run(df, signal_column=sig_col)
                results[code] = result
            else:
                results[code] = {'error': 'Backtester not initialized'}
        
        return results
    
    # ==================== 计算工具 ====================
    
    def _annualized(self, total_return: float, days: int) -> float:
        """年化收益率"""
        if days <= 0:
            return 0.0
        years = days / 252  # 252交易日
        if years <= 0:
            return 0.0
        return (1 + total_return) ** (1 / years) - 1
    
    def _max_drawdown_from_values(self, values: List[float]) -> float:
        """从价值序列计算最大回撤"""
        if len(values) < 2:
            return 0.0
        
        max_dd = 0.0
        peak = values[0]
        
        for value in values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def _sharpe(self, daily_returns: List[float]) -> float:
        """夏普比率（年化）"""
        if len(daily_returns) < 2:
            return 0.0
        
        returns_np = np.array(daily_returns)
        mean_return = returns_np.mean()
        std_return = returns_np.std()
        
        if std_return == 0:
            return 0.0
        
        # 假设无风险利率 2% 年化
        risk_free = 0.02 / 252
        sharpe = (mean_return - risk_free) / std_return * np.sqrt(252)
        
        return sharpe
    
    def _create_comparison_report(self, values: List[float],
                                  dates: List[str],
                                  daily_returns: List[float],
                                  initial_capital: float) -> dict:
        """创建组合对比报告"""
        total_return = (values[-1] - initial_capital) / initial_capital
        annualized = self._annualized(total_return, len(dates))
        max_dd = self._max_drawdown_from_values(values)
        sharpe = self._sharpe(daily_returns)
        
        return {
            'total_return': round(total_return * 100, 2),
            'annualized_return': round(annualized * 100, 2),
            'max_drawdown': round(max_dd * 100, 2),
            'sharpe_ratio': round(sharpe, 2),
            'final_value': round(values[-1], 2)
        }


# ==================== 快捷函数 ====================

def multi_index_backtest(df_list: List[pd.DataFrame],
                        code_list: List[str],
                        name_list: List[str],
                        signal_columns: List[str] = None,
                        initial_capital: float = 100000,
                        commission_rate: float = 0.00006) -> dict:
    """
    快捷多指数回测函数
    
    Args:
        df_list: 各指数DataFrame
        code_list: 各指数代码
        name_list: 各指数名称
        signal_columns: 信号列名
        initial_capital: 初始资金
        commission_rate: 佣金率
    
    Returns:
        dict: 回测结果
    """
    mib = MultiIndexBacktester(
        initial_capital=initial_capital,
        commission_rate=commission_rate
    )
    
    if signal_columns is None:
        signal_columns = ['final_signal'] * len(df_list)
    
    return mib.run(
        df_list=df_list,
        code_list=code_list,
        name_list=name_list,
        signal_columns=signal_columns
    )
