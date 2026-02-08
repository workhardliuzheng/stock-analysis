"""
多图表生成器

为指数分析生成6种类型的可视化图表
每张图表都在右上角显示最新日期的关键指标
"""

import os
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime

from entity import constant
from analysis.cross_signal_detector import CrossSignalDetector
from analysis.percentile_calculator import PercentileCalculator

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class IndexChartGenerator:
    """
    指数分析图表生成器
    
    生成6种分析图表：
    1. 价格与均线全景图
    2. 偏离率与历史百分位图
    3. MACD分析图
    4. 成交量历史百分位图
    5. 估值指标对比图
    6. 综合技术指标面板
    """
    
    # 颜色配置
    COLORS = {
        'price': '#E74C3C',      # 红色 - 收盘价
        'ma_5': '#3498DB',       # 蓝色 - MA5
        'ma_10': '#2ECC71',      # 绿色 - MA10
        'ma_20': '#F39C12',      # 橙色 - MA20
        'ma_50': '#9B59B6',      # 紫色 - MA50
        'volume_up': '#E74C3C',  # 红色 - 上涨
        'volume_down': '#27AE60',# 绿色 - 下跌
        'macd': '#3498DB',       # 蓝色 - MACD
        'signal': '#E67E22',     # 橙色 - 信号线
        'hist_pos': '#E74C3C',   # 红色 - 正柱
        'hist_neg': '#27AE60',   # 绿色 - 负柱
        'golden': '#27AE60',     # 绿色 - 金叉
        'death': '#E74C3C',      # 红色 - 死叉
        'latest': '#FF6B35',     # 橙色 - 最新点
    }
    
    def __init__(self):
        self.cross_detector = CrossSignalDetector()
        self.percentile_calculator = PercentileCalculator()
    
    def generate_all_charts(self, df: pd.DataFrame, ts_code: str, name: str,
                            save_dir: str = None, show: bool = False):
        """
        生成所有6张分析图表
        
        Args:
            df: 包含分析数据的DataFrame
            ts_code: 指数代码
            name: 指数名称
            save_dir: 保存目录
            show: 是否显示图表
        """
        if len(df) == 0:
            print(f"警告: {name} 没有数据，跳过图表生成")
            return
        
        # 创建保存目录
        if save_dir:
            index_dir = os.path.join(save_dir, name)
            os.makedirs(index_dir, exist_ok=True)
        else:
            index_dir = None
        
        # 生成6张图表
        charts = [
            ('01_价格均线图', self.plot_price_ma_chart),
            ('02_偏离率百分位图', self.plot_deviation_percentile_chart),
            ('03_MACD分析图', self.plot_macd_chart),
            ('04_成交量百分位图', self.plot_volume_percentile_chart),
            ('05_估值指标图', self.plot_valuation_chart),
            ('06_技术指标面板', self.plot_technical_panel_chart),
        ]
        
        for chart_name, plot_func in charts:
            try:
                save_path = os.path.join(index_dir, f'{chart_name}.png') if index_dir else None
                plot_func(df, ts_code, name, save_path=save_path, show=show)
                print(f"  生成: {chart_name}")
            except Exception as e:
                print(f"  生成 {chart_name} 失败: {e}")
    
    def plot_price_ma_chart(self, df: pd.DataFrame, ts_code: str, name: str,
                            save_path: str = None, show: bool = False):
        """
        图1: 价格与均线全景图
        - 上半部: 收盘价 + MA5/MA10/MA20/MA50
        - 下半部: 成交量柱状图
        - 标注: 金叉死叉点、最新数据信息框
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                        gridspec_kw={'height_ratios': [3, 1]})
        fig.suptitle(f'{name} - 价格与均线分析', fontsize=14, fontweight='bold')
        
        x = df['trade_date']
        
        # 上半部：价格和均线
        ax1.plot(x, df['close'], label='收盘价', color=self.COLORS['price'], linewidth=1.5)
        
        if 'ma_5' in df.columns:
            ax1.plot(x, df['ma_5'], label='MA5', color=self.COLORS['ma_5'], linewidth=1)
        if 'ma_10' in df.columns:
            ax1.plot(x, df['ma_10'], label='MA10', color=self.COLORS['ma_10'], linewidth=1)
        if 'ma_20' in df.columns:
            ax1.plot(x, df['ma_20'], label='MA20', color=self.COLORS['ma_20'], linewidth=1)
        if 'ma_50' in df.columns:
            ax1.plot(x, df['ma_50'], label='MA50', color=self.COLORS['ma_50'], linewidth=1)
        
        # 标注金叉死叉点
        self._mark_cross_signals(ax1, df, 'ma_5_10')
        
        # 标记最新点
        self._mark_latest_point(ax1, df, 'close')
        
        ax1.set_ylabel('价格', fontsize=10)
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        # 下半部：成交量
        colors = [self.COLORS['volume_up'] if df['pct_chg'].iloc[i] >= 0 
                  else self.COLORS['volume_down'] for i in range(len(df))]
        ax2.bar(x, df['amount'] / 1e8, color=colors, alpha=0.7, width=1)
        ax2.set_ylabel('成交额(亿)', fontsize=10)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        # 添加信息框
        latest = df.iloc[-1]
        info_lines = self._build_price_ma_info(df, latest)
        self._add_info_box(ax1, info_lines)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        plt.close()
    
    def plot_deviation_percentile_chart(self, df: pd.DataFrame, ts_code: str, name: str,
                                         save_path: str = None, show: bool = False):
        """
        图2: 偏离率与历史百分位
        - 左Y轴: 各均线偏离率
        - 右Y轴: 偏离率历史百分位
        """
        fig, ax1 = plt.subplots(figsize=(14, 7))
        fig.suptitle(f'{name} - 偏离率与历史百分位', fontsize=14, fontweight='bold')
        
        x = df['trade_date']
        
        # 解析偏离率数据
        deviation_data = self._parse_json_column(df, 'deviation_rate')
        percentile_data = self._parse_json_column(df, 'percentile_ranks')
        
        # 左轴：偏离率
        colors = [self.COLORS['ma_5'], self.COLORS['ma_10'], 
                  self.COLORS['ma_20'], self.COLORS['ma_50']]
        ma_keys = ['ma_5', 'ma_10', 'ma_20', 'ma_50']
        
        for i, key in enumerate(ma_keys):
            if key in deviation_data.columns:
                ax1.plot(x, deviation_data[key] * 100, label=f'{key}偏离率%', 
                        color=colors[i], linewidth=1)
        
        ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax1.axhline(y=5, color='red', linestyle=':', alpha=0.3, label='±5%警戒线')
        ax1.axhline(y=-5, color='green', linestyle=':', alpha=0.3)
        ax1.set_ylabel('偏离率 (%)', fontsize=10)
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        
        # 右轴：百分位
        ax2 = ax1.twinx()
        if 'deviation_ma_20' in percentile_data.columns:
            ax2.fill_between(x, percentile_data['deviation_ma_20'], 
                            alpha=0.2, color='purple', label='MA20偏离率百分位')
            ax2.plot(x, percentile_data['deviation_ma_20'], 
                    color='purple', linewidth=1, alpha=0.7)
        ax2.set_ylabel('历史百分位 (%)', fontsize=10)
        ax2.set_ylim(0, 100)
        
        # 标记最新点
        if 'deviation_ma_20' in percentile_data.columns:
            self._mark_latest_point(ax2, percentile_data, 'deviation_ma_20', color='purple')
        
        # 添加信息框
        latest = df.iloc[-1]
        info_lines = self._build_deviation_info(deviation_data, percentile_data, latest)
        self._add_info_box(ax1, info_lines)
        
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        plt.close()
    
    def plot_macd_chart(self, df: pd.DataFrame, ts_code: str, name: str,
                        save_path: str = None, show: bool = False):
        """
        图3: MACD分析图
        - 上半部: MACD与信号线
        - 下半部: 柱状图（红绿柱）
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), 
                                        gridspec_kw={'height_ratios': [1, 1]})
        fig.suptitle(f'{name} - MACD分析', fontsize=14, fontweight='bold')
        
        x = df['trade_date']
        
        # 上半部：MACD和信号线
        if 'macd' in df.columns:
            ax1.plot(x, df['macd'], label='MACD', color=self.COLORS['macd'], linewidth=1.2)
        if 'macd_signal_line' in df.columns:
            ax1.plot(x, df['macd_signal_line'], label='信号线', 
                    color=self.COLORS['signal'], linewidth=1.2)
        
        ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        
        # 标注MACD金叉死叉
        self._mark_cross_signals(ax1, df, 'macd')
        
        ax1.set_ylabel('MACD', fontsize=10)
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        # 下半部：柱状图
        if 'macd_histogram' in df.columns:
            colors = [self.COLORS['hist_pos'] if v >= 0 else self.COLORS['hist_neg'] 
                     for v in df['macd_histogram']]
            ax2.bar(x, df['macd_histogram'], color=colors, alpha=0.7, width=1)
        
        ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax2.set_ylabel('MACD柱状图', fontsize=10)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        # 添加信息框
        latest = df.iloc[-1]
        info_lines = self._build_macd_info(df, latest)
        self._add_info_box(ax1, info_lines)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        plt.close()
    
    def plot_volume_percentile_chart(self, df: pd.DataFrame, ts_code: str, name: str,
                                      save_path: str = None, show: bool = False):
        """
        图4: 成交量历史百分位
        """
        fig, ax1 = plt.subplots(figsize=(14, 7))
        fig.suptitle(f'{name} - 成交量历史百分位', fontsize=14, fontweight='bold')
        
        x = df['trade_date']
        
        # 成交量柱状图
        colors = [self.COLORS['volume_up'] if df['pct_chg'].iloc[i] >= 0 
                  else self.COLORS['volume_down'] for i in range(len(df))]
        ax1.bar(x, df['amount'] / 1e8, color=colors, alpha=0.6, width=1, label='成交额(亿)')
        ax1.set_ylabel('成交额 (亿)', fontsize=10)
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        
        # 右轴：百分位
        ax2 = ax1.twinx()
        percentile_data = self._parse_json_column(df, 'percentile_ranks')
        if 'amount' in percentile_data.columns:
            ax2.plot(x, percentile_data['amount'], color='purple', 
                    linewidth=1.5, label='成交额百分位')
            ax2.fill_between(x, percentile_data['amount'], alpha=0.1, color='purple')
            
            # 标记最新点
            self._mark_latest_point(ax2, percentile_data, 'amount', color='purple')
        
        ax2.set_ylabel('历史百分位 (%)', fontsize=10)
        ax2.set_ylim(0, 100)
        ax2.axhline(y=80, color='red', linestyle=':', alpha=0.5, label='80%高位线')
        ax2.axhline(y=20, color='green', linestyle=':', alpha=0.5, label='20%低位线')
        ax2.legend(loc='upper right', fontsize=8)
        
        # 添加信息框
        latest = df.iloc[-1]
        info_lines = self._build_volume_info(df, percentile_data, latest)
        self._add_info_box(ax1, info_lines, position='upper center')
        
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        plt.close()
    
    def plot_valuation_chart(self, df: pd.DataFrame, ts_code: str, name: str,
                              save_path: str = None, show: bool = False):
        """
        图5: 估值指标对比
        """
        fig, ax1 = plt.subplots(figsize=(14, 7))
        fig.suptitle(f'{name} - 估值指标分析', fontsize=14, fontweight='bold')
        
        x = df['trade_date']
        
        # 左轴：收盘价
        ax1.plot(x, df['close'], label='收盘价', color=self.COLORS['price'], linewidth=1.5)
        ax1.set_ylabel('价格', fontsize=10)
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        
        # 右轴：PE/PB
        ax2 = ax1.twinx()
        has_data = False
        if 'pe_ttm' in df.columns and df['pe_ttm'].notna().any():
            ax2.plot(x, df['pe_ttm'], label='PE-TTM', color='blue', linewidth=1)
            has_data = True
        if 'pb' in df.columns and df['pb'].notna().any():
            ax2.plot(x, df['pb'], label='PB', color='green', linewidth=1)
            has_data = True
        
        if has_data:
            ax2.set_ylabel('PE / PB', fontsize=10)
            ax2.legend(loc='upper right', fontsize=8)
        
        # 添加信息框
        latest = df.iloc[-1]
        percentile_data = self._parse_json_column(df, 'percentile_ranks')
        info_lines = self._build_valuation_info(latest, percentile_data)
        self._add_info_box(ax1, info_lines)
        
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        plt.close()
    
    def plot_technical_panel_chart(self, df: pd.DataFrame, ts_code: str, name: str,
                                    save_path: str = None, show: bool = False):
        """
        图6: 综合技术指标面板
        - 子图1: RSI
        - 子图2: KDJ
        - 子图3: 布林带
        """
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12), 
                                             gridspec_kw={'height_ratios': [1, 1, 1.5]})
        fig.suptitle(f'{name} - 综合技术指标', fontsize=14, fontweight='bold')
        
        x = df['trade_date']
        
        # 子图1: RSI
        if 'rsi' in df.columns:
            ax1.plot(x, df['rsi'], label='RSI(14)', color='purple', linewidth=1.2)
            ax1.axhline(y=70, color='red', linestyle='--', alpha=0.5, label='超买线(70)')
            ax1.axhline(y=30, color='green', linestyle='--', alpha=0.5, label='超卖线(30)')
            ax1.axhline(y=50, color='gray', linestyle=':', alpha=0.3)
            ax1.fill_between(x, 70, 100, alpha=0.1, color='red')
            ax1.fill_between(x, 0, 30, alpha=0.1, color='green')
            self._mark_latest_point(ax1, df, 'rsi', color='purple')
        ax1.set_ylabel('RSI', fontsize=10)
        ax1.set_ylim(0, 100)
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        
        # 子图2: KDJ
        if 'kdj_k' in df.columns:
            ax2.plot(x, df['kdj_k'], label='K', color='blue', linewidth=1)
        if 'kdj_d' in df.columns:
            ax2.plot(x, df['kdj_d'], label='D', color='orange', linewidth=1)
        if 'kdj_j' in df.columns:
            ax2.plot(x, df['kdj_j'], label='J', color='purple', linewidth=1)
        ax2.axhline(y=80, color='red', linestyle='--', alpha=0.5)
        ax2.axhline(y=20, color='green', linestyle='--', alpha=0.5)
        ax2.set_ylabel('KDJ', fontsize=10)
        ax2.legend(loc='upper left', fontsize=8)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        
        # 子图3: 布林带
        ax3.plot(x, df['close'], label='收盘价', color=self.COLORS['price'], linewidth=1.2)
        if 'bb_high' in df.columns:
            ax3.plot(x, df['bb_high'], label='上轨', color='gray', linewidth=0.8, linestyle='--')
        if 'bb_mid' in df.columns:
            ax3.plot(x, df['bb_mid'], label='中轨', color='blue', linewidth=0.8)
        if 'bb_low' in df.columns:
            ax3.plot(x, df['bb_low'], label='下轨', color='gray', linewidth=0.8, linestyle='--')
        if 'bb_high' in df.columns and 'bb_low' in df.columns:
            ax3.fill_between(x, df['bb_low'], df['bb_high'], alpha=0.1, color='blue')
        ax3.set_ylabel('价格', fontsize=10)
        ax3.legend(loc='upper left', fontsize=8)
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        
        # 添加信息框
        latest = df.iloc[-1]
        info_lines = self._build_technical_info(latest)
        self._add_info_box(ax1, info_lines)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        plt.close()
    
    # ==================== 辅助方法 ====================
    
    def _parse_json_column(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """解析JSON列为DataFrame"""
        data_list = []
        for _, row in df.iterrows():
            json_str = row.get(column, '')
            try:
                data = json.loads(json_str) if json_str else {}
            except (json.JSONDecodeError, TypeError):
                data = {}
            data_list.append(data)
        
        result = pd.DataFrame(data_list, index=df.index)
        result['trade_date'] = df['trade_date'].values
        return result
    
    def _mark_latest_point(self, ax, df: pd.DataFrame, column: str, color: str = None):
        """在曲线最后一个点添加醒目标记"""
        if column not in df.columns or len(df) == 0:
            return
        
        x = df['trade_date'].iloc[-1]
        y = df[column].iloc[-1]
        
        if pd.isna(y):
            return
        
        color = color or self.COLORS['latest']
        ax.scatter([x], [y], s=100, c=color, zorder=5, 
                  edgecolors='black', linewidths=1.5)
        ax.axvline(x=x, color='gray', linestyle='--', alpha=0.3, linewidth=1)
    
    def _mark_cross_signals(self, ax, df: pd.DataFrame, signal_key: str):
        """标注金叉死叉点"""
        if 'cross_signals' not in df.columns:
            return
        
        for i, row in df.iterrows():
            signals = self.cross_detector.parse_signal_json(row.get('cross_signals', ''))
            signal = signals.get(signal_key)
            
            if signal == 'golden_cross':
                ax.scatter([row['trade_date']], [row['close']], 
                          marker='^', s=80, c=self.COLORS['golden'], 
                          zorder=4, edgecolors='black', linewidths=0.5)
            elif signal == 'death_cross':
                ax.scatter([row['trade_date']], [row['close']], 
                          marker='v', s=80, c=self.COLORS['death'], 
                          zorder=4, edgecolors='black', linewidths=0.5)
    
    def _add_info_box(self, ax, lines: List[str], position: str = 'upper right'):
        """在图表上添加信息框"""
        if not lines:
            return
        
        text = '\n'.join(lines)
        props = dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.9)
        
        if position == 'upper right':
            x, y = 0.98, 0.98
            ha, va = 'right', 'top'
        elif position == 'upper center':
            x, y = 0.5, 0.98
            ha, va = 'center', 'top'
        else:
            x, y = 0.98, 0.98
            ha, va = 'right', 'top'
        
        ax.text(x, y, text, transform=ax.transAxes, fontsize=9,
                verticalalignment=va, horizontalalignment=ha,
                bbox=props, family='monospace')
    
    def _build_price_ma_info(self, df: pd.DataFrame, latest: pd.Series) -> List[str]:
        """构建价格均线信息框内容"""
        trade_date = latest.get('trade_date', '')
        if hasattr(trade_date, 'strftime'):
            trade_date = trade_date.strftime('%Y-%m-%d')
        
        lines = [
            f"最新日期: {trade_date}",
            f"─────────────────",
            f"收盘价: {latest.get('close', 0):.2f}",
            f"涨跌幅: {latest.get('pct_chg', 0):.2f}%",
        ]
        
        # 均线
        for period in [5, 10, 20, 50]:
            ma_val = latest.get(f'ma_{period}')
            if ma_val and not pd.isna(ma_val):
                lines.append(f"MA{period}: {ma_val:.2f}")
        
        # 最近金叉死叉
        gc = self.cross_detector.find_latest_cross_date(df, 'golden_cross', 'ma_5_10')
        dc = self.cross_detector.find_latest_cross_date(df, 'death_cross', 'ma_5_10')
        
        lines.append(f"─────────────────")
        if gc:
            lines.append(f"MA5-10金叉: {gc[1]}天前")
        if dc:
            lines.append(f"MA5-10死叉: {dc[1]}天前")
        
        return lines
    
    def _build_deviation_info(self, deviation_data: pd.DataFrame, 
                               percentile_data: pd.DataFrame,
                               latest: pd.Series) -> List[str]:
        """构建偏离率信息框内容"""
        trade_date = latest.get('trade_date', '')
        if hasattr(trade_date, 'strftime'):
            trade_date = trade_date.strftime('%Y-%m-%d')
        
        lines = [
            f"最新日期: {trade_date}",
            f"─────────────────",
        ]
        
        idx = latest.name
        for key in ['ma_5', 'ma_10', 'ma_20', 'ma_50']:
            dev_val = deviation_data[key].iloc[-1] if key in deviation_data.columns else None
            pct_key = f'deviation_{key}'
            pct_val = percentile_data[pct_key].iloc[-1] if pct_key in percentile_data.columns else None
            
            if dev_val is not None and not pd.isna(dev_val):
                dev_str = f"{dev_val*100:+.2f}%"
                pct_str = f"({pct_val:.0f}%分位)" if pct_val and not pd.isna(pct_val) else ""
                lines.append(f"{key}偏离: {dev_str} {pct_str}")
        
        return lines
    
    def _build_macd_info(self, df: pd.DataFrame, latest: pd.Series) -> List[str]:
        """构建MACD信息框内容"""
        trade_date = latest.get('trade_date', '')
        if hasattr(trade_date, 'strftime'):
            trade_date = trade_date.strftime('%Y-%m-%d')
        
        macd = latest.get('macd', 0)
        signal = latest.get('macd_signal_line', 0)
        hist = latest.get('macd_histogram', 0)
        
        # 柱状图趋势
        signals = self.cross_detector.parse_signal_json(latest.get('cross_signals', ''))
        trend = signals.get('macd_hist_trend', '')
        trend_text = {
            'red_longer': '红柱变长',
            'red_shorter': '红柱变短',
            'green_longer': '绿柱变长',
            'green_shorter': '绿柱变短',
        }.get(trend, '无明显趋势')
        
        lines = [
            f"最新日期: {trade_date}",
            f"─────────────────",
            f"MACD: {macd:.4f}" if macd else "MACD: N/A",
            f"信号线: {signal:.4f}" if signal else "信号线: N/A",
            f"柱状图: {hist:.4f}" if hist else "柱状图: N/A",
            f"柱状趋势: {trend_text}",
        ]
        
        # 最近金叉死叉
        gc = self.cross_detector.find_latest_cross_date(df, 'golden_cross', 'macd')
        dc = self.cross_detector.find_latest_cross_date(df, 'death_cross', 'macd')
        
        lines.append(f"─────────────────")
        if gc:
            lines.append(f"MACD金叉: {gc[1]}天前")
        if dc:
            lines.append(f"MACD死叉: {dc[1]}天前")
        
        return lines
    
    def _build_volume_info(self, df: pd.DataFrame, percentile_data: pd.DataFrame,
                           latest: pd.Series) -> List[str]:
        """构建成交量信息框内容"""
        trade_date = latest.get('trade_date', '')
        if hasattr(trade_date, 'strftime'):
            trade_date = trade_date.strftime('%Y-%m-%d')
        
        amount = latest.get('amount', 0) / 1e8  # 转换为亿
        vol = latest.get('vol', 0) / 1e4  # 转换为万手
        
        pct_amount = percentile_data['amount'].iloc[-1] if 'amount' in percentile_data.columns else None
        level = self.percentile_calculator.get_percentile_level(pct_amount) if pct_amount else '未知'
        
        lines = [
            f"最新日期: {trade_date}",
            f"─────────────────",
            f"成交额: {amount:.2f}亿",
            f"成交量: {vol:.2f}万手",
        ]
        
        if pct_amount is not None and not pd.isna(pct_amount):
            lines.append(f"百分位: {pct_amount:.1f}% ({level})")
        
        return lines
    
    def _build_valuation_info(self, latest: pd.Series, 
                               percentile_data: pd.DataFrame) -> List[str]:
        """构建估值信息框内容"""
        trade_date = latest.get('trade_date', '')
        if hasattr(trade_date, 'strftime'):
            trade_date = trade_date.strftime('%Y-%m-%d')
        
        lines = [
            f"最新日期: {trade_date}",
            f"─────────────────",
        ]
        
        for key, label in [('pe_ttm', 'PE-TTM'), ('pb', 'PB'), 
                           ('pe_weight', 'PE加权'), ('pb_weight', 'PB加权')]:
            val = latest.get(key)
            if val and not pd.isna(val):
                pct_val = percentile_data[key].iloc[-1] if key in percentile_data.columns else None
                pct_str = f" ({pct_val:.0f}%分位)" if pct_val and not pd.isna(pct_val) else ""
                lines.append(f"{label}: {val:.2f}{pct_str}")
        
        return lines
    
    def _build_technical_info(self, latest: pd.Series) -> List[str]:
        """构建技术指标信息框内容"""
        trade_date = latest.get('trade_date', '')
        if hasattr(trade_date, 'strftime'):
            trade_date = trade_date.strftime('%Y-%m-%d')
        
        rsi = latest.get('rsi')
        kdj_k = latest.get('kdj_k')
        kdj_d = latest.get('kdj_d')
        kdj_j = latest.get('kdj_j')
        
        rsi_status = '超买' if rsi and rsi > 70 else ('超卖' if rsi and rsi < 30 else '中性')
        kdj_status = '超买' if kdj_k and kdj_k > 80 else ('超卖' if kdj_k and kdj_k < 20 else '中性')
        
        lines = [
            f"最新日期: {trade_date}",
            f"─────────────────",
        ]
        
        if rsi is not None and not pd.isna(rsi):
            lines.append(f"RSI(14): {rsi:.2f} ({rsi_status})")
        
        if kdj_k is not None and not pd.isna(kdj_k):
            lines.append(f"KDJ_K: {kdj_k:.2f} ({kdj_status})")
        if kdj_d is not None and not pd.isna(kdj_d):
            lines.append(f"KDJ_D: {kdj_d:.2f}")
        if kdj_j is not None and not pd.isna(kdj_j):
            lines.append(f"KDJ_J: {kdj_j:.2f}")
        
        # 布林带位置
        close = latest.get('close')
        bb_high = latest.get('bb_high')
        bb_low = latest.get('bb_low')
        if close and bb_high and bb_low and bb_high != bb_low:
            bb_pos = (close - bb_low) / (bb_high - bb_low) * 100
            lines.append(f"─────────────────")
            lines.append(f"布林带位置: {bb_pos:.1f}%")
        
        return lines
