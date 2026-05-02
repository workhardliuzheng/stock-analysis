"""
持仓记录与追踪系统

记录用户的实际买卖操作，计算盈亏，匹配信号给出操作建议。

设计原则:
1. 纯文件操作 (positions.csv)，不依赖数据库
2. 不修改现有系统任何代码
3. 双向交互: 用户告知操作 -> 系统记录 -> 日报反馈

用法:
    from position_tracker import PositionTracker
    
    tracker = PositionTracker()
    
    # 买入
    tracker.buy('518880.SH', '黄金ETF', 'ETF', '2026-04-15', 5.32, 1000)
    
    # 卖出
    tracker.sell('518880.SH', '2026-05-06', 5.50)
    
    # 查看持仓
    positions = tracker.get_current_positions()
    
    # 查看日报数据
    summary = tracker.get_daily_summary(current_prices)
"""

import csv
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

POSITIONS_FILE = os.path.join(os.path.dirname(__file__), 'positions.csv')
FIELDS = ['id', 'code', 'name', 'type', 'buy_date', 'buy_price', 'quantity',
          'status', 'sell_date', 'sell_price', 'pnl', 'created_at', 'updated_at']


class PositionTracker:

    def __init__(self, csv_path: str = POSITIONS_FILE):
        self.csv_path = csv_path
        self._init_file()

    def _init_file(self):
        """如果文件不存在，创建并写表头"""
        if not os.path.exists(self.csv_path):
            os.makedirs(os.path.dirname(self.csv_path) or '.', exist_ok=True)
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(FIELDS)

    # ==================== 读写操作 ====================

    def _read_all(self) -> List[dict]:
        """读取全部持仓记录"""
        rows = []
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
        return rows

    def _write_all(self, rows: List[dict]):
        """覆盖写入全部记录"""
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def _next_id(self, rows: List[dict]) -> int:
        return max((int(r['id']) for r in rows if r['id']), default=0) + 1

    # ==================== 核心操作 ====================

    def buy(self, code: str, name: str, type_: str,
            buy_date: str, buy_price: float, quantity: float) -> int:
        """
        记录买入操作

        Args:
            code: 代码 (如 518880.SH / 300ETF / 113566)
            name: 名称 (如 黄金ETF / 沪深300ETF / 好客转债)
            type_: 品种 (ETF / 可转债)
            buy_date: 买入日期 (YYYY-MM-DD)
            buy_price: 买入单价
            quantity: 数量 (ETF为股数/可转债为张数)

        Returns:
            记录ID
        """
        rows = self._read_all()
        new_id = self._next_id(rows)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        rows.append({
            'id': str(new_id),
            'code': code,
            'name': name,
            'type': type_,
            'buy_date': buy_date,
            'buy_price': str(buy_price),
            'quantity': str(quantity),
            'status': '持有',
            'sell_date': '',
            'sell_price': '',
            'pnl': '',
            'created_at': now,
            'updated_at': now,
        })
        self._write_all(rows)
        cost = buy_price * quantity
        print(f"  [持仓记录] 买入 {name} ({code}) x{quantity}"
              f" @ {buy_price} = {cost:.2f} 元 (ID={new_id})")
        return new_id

    def sell(self, code: str, sell_date: str, sell_price: float,
             quantity: Optional[float] = None) -> bool:
        """
        记录卖出操作

        如果 quantity 未指定，卖出该代码的全部持仓。
        如果是部分卖出，扣减对应数量的持仓（先进先出）。

        Args:
            code: 代码
            sell_date: 卖出日期 (YYYY-MM-DD)
            sell_price: 卖出单价
            quantity: 卖出数量 (None=全卖)

        Returns:
            是否成功
        """
        rows = self._read_all()
        open_positions = [r for r in rows
                          if r['code'] == code and r['status'] == '持有']

        if not open_positions:
            print(f"  [WARN] 没有找到 {code} 的持仓记录")
            return False

        to_sell_qty = quantity or sum(float(r['quantity']) for r in open_positions)
        remaining = to_sell_qty
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        for pos in sorted(open_positions, key=lambda r: r['buy_date']):
            if remaining <= 0:
                break
            pos_qty = float(pos['quantity'])
            if pos_qty <= remaining:
                # 整笔卖出
                pos['status'] = '已卖出'
                pos['sell_date'] = sell_date
                pos['sell_price'] = str(sell_price)
                cost = float(pos['buy_price']) * pos_qty
                proceeds = sell_price * pos_qty
                pnl = proceeds - cost
                pos['pnl'] = f"{pnl:.2f}"
                pos['updated_at'] = now
                remaining -= pos_qty
                name = pos['name']
                print(f"  [持仓记录] 卖出 {name} ({code}) x{pos_qty}"
                      f" @ {sell_price}, 盈亏 {pnl:+.2f}")
            else:
                # 部分卖出: 拆分记录
                pos['quantity'] = str(pos_qty - remaining)
                pos['updated_at'] = now
                # 新增一条卖出记录
                rows.append({
                    'id': str(self._next_id(rows)),
                    'code': code,
                    'name': pos['name'],
                    'type': pos['type'],
                    'buy_date': pos['buy_date'],
                    'buy_price': pos['buy_price'],
                    'quantity': str(remaining),
                    'status': '已卖出',
                    'sell_date': sell_date,
                    'sell_price': str(sell_price),
                    'pnl': f"{(sell_price - float(pos['buy_price'])) * remaining:.2f}",
                    'created_at': pos['created_at'],
                    'updated_at': now,
                })
                cost = float(pos['buy_price']) * remaining
                proceeds = sell_price * remaining
                print(f"  [持仓记录] 部分卖出 {pos['name']} ({code})"
                      f" x{remaining} @ {sell_price}, 盈亏 {proceeds - cost:+.2f}")
                remaining = 0

        self._write_all(rows)
        return True

    # ==================== 查询 ====================

    def get_current_positions(self) -> List[dict]:
        """获取当前持仓（未卖出的）"""
        rows = self._read_all()
        return [r for r in rows if r['status'] == '持有']

    def get_position_by_code(self, code: str) -> List[dict]:
        """获取某代码的所有记录"""
        rows = self._read_all()
        return [r for r in rows if r['code'] == code]

    def get_history(self) -> List[dict]:
        """获取全部记录"""
        return self._read_all()

    # ==================== 盈亏计算 ====================

    def get_cost_basis(self, code: str) -> float:
        """计算某代码持仓的加权平均成本"""
        positions = [r for r in self._read_all()
                     if r['code'] == code and r['status'] == '持有']
        if not positions:
            return 0.0
        total_cost = sum(float(r['buy_price']) * float(r['quantity']) for r in positions)
        total_qty = sum(float(r['quantity']) for r in positions)
        return total_cost / total_qty if total_qty > 0 else 0.0

    def get_total_cost(self) -> float:
        """总投入成本（含已卖出的）"""
        rows = self._read_all()
        total = 0.0
        for r in rows:
            total += float(r['buy_price']) * float(r['quantity'])
        return total

    def get_current_value(self, current_prices: Dict[str, float]) -> float:
        """按当前市价计算持仓市值"""
        positions = self.get_current_positions()
        value = 0.0
        for p in positions:
            price = current_prices.get(p['code'])
            if price:
                value += price * float(p['quantity'])
        return value

    def get_realized_pnl(self) -> float:
        """已实现盈亏（已卖出记录的pnl总和）"""
        rows = self._read_all()
        total = 0.0
        for r in rows:
            if r['status'] == '已卖出' and r['pnl']:
                try:
                    total += float(r['pnl'])
                except ValueError:
                    pass
        return total

    def get_unrealized_pnl(self, current_prices: Dict[str, float]) -> float:
        """未实现盈亏（持仓按市价 - 成本）"""
        positions = self.get_current_positions()
        total = 0.0
        for p in positions:
            price = current_prices.get(p['code'])
            if price:
                cost = float(p['buy_price']) * float(p['quantity'])
                value = price * float(p['quantity'])
                total += value - cost
        return total

    # ==================== 日报数据 ====================

    def get_daily_summary(self, current_prices: Dict[str, float]) -> dict:
        """
        生成日报用的账户摘要

        Args:
            current_prices: {code: current_price} 当前价格字典

        Returns:
            {
                'total_cost': float,       # 总投入
                'current_value': float,     # 当前市值
                'total_pnl': float,         # 总盈亏(含已实现)
                'total_pnl_pct': float,     # 总盈亏百分比
                'positions': [              # 每笔持仓详情
                    {
                        'code': str,
                        'name': str,
                        'type': str,
                        'buy_date': str,
                        'buy_price': float,
                        'quantity': float,
                        'current_price': float,
                        'cost': float,
                        'value': float,
                        'pnl': float,
                        'pnl_pct': float,
                        'signal': str,      # 待匹配
                    }
                ]
            }
        """
        positions = self.get_current_positions()
        total_cost = 0.0
        current_value = 0.0
        position_details = []

        for p in positions:
            price = current_prices.get(p['code'], 0.0)
            cost = float(p['buy_price']) * float(p['quantity'])
            value = price * float(p['quantity'])
            total_cost += cost
            current_value += value
            pnl = value - cost
            pnl_pct = (pnl / cost * 100) if cost > 0 else 0.0

            position_details.append({
                'code': p['code'],
                'name': p['name'],
                'type': p['type'],
                'buy_date': p['buy_date'],
                'buy_price': float(p['buy_price']),
                'quantity': float(p['quantity']),
                'current_price': price,
                'cost': cost,
                'value': value,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'signal': '',  # 由外部匹配
            })

        realized_pnl = self.get_realized_pnl()
        total_pnl = (current_value - total_cost) + realized_pnl
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0

        return {
            'total_cost': total_cost,
            'current_value': current_value,
            'realized_pnl': realized_pnl,
            'unrealized_pnl': current_value - total_cost,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'positions': position_details,
        }

    def match_signals(self, summary: dict,
                      signal_map: Dict[str, str],
                      cb_recommendations: Optional[List[str]] = None) -> list:
        """
        为持仓匹配今日信号，生成操作建议

        Args:
            summary: get_daily_summary 的返回值
            signal_map: {code: 'BUY'/'SELL'/'HOLD'}
            cb_recommendations: 可转债推荐买入名单（双低Top N）

        Returns:
            [ {code, name, type, signal, action, reason}, ... ]
        """
        advices = []
        for pos in summary['positions']:
            code = pos['code']
            signal = signal_map.get(code, '')

            action = '持有'
            reason = ''

            if pos['type'] == '可转债':
                # 可转债: 看是否在推荐名单
                if cb_recommendations and code in cb_recommendations:
                    action = '持有/加仓'
                    reason = '双低排名靠前，建议持有'
                elif cb_recommendations and code not in cb_recommendations:
                    action = '关注卖出'
                    reason = '不在双低Top推荐，轮动时可考虑卖出'
                # 止损检查
                if pos['current_price'] < 80:
                    action = '[WARN] 止损卖出'
                    reason = '价格跌破80元底线，强制止损'

            elif pos['type'] == 'ETF':
                if signal == 'BUY' or signal == 'HOLD':
                    action = '持有'
                    reason = f'信号: {signal}'
                elif signal == 'SELL':
                    action = '考虑卖出'
                    reason = f'信号: {signal}，建议减仓'

                # 浮盈/浮亏提醒
                if pos['pnl_pct'] > 20:
                    action = '注意止盈'
                    if reason:
                        reason += '，'
                    reason += f'浮盈 {pos["pnl_pct"]:.1f}% 已达到止盈区间'
                elif pos['pnl_pct'] < -15:
                    action = '[WARN] 注意风险'
                    if reason:
                        reason += '，'
                    reason += f'浮亏 {pos["pnl_pct"]:.1f}% 超过15%'

            advices.append({
                'code': code,
                'name': pos['name'],
                'type': pos['type'],
                'signal': signal,
                'action': action,
                'reason': reason,
                'pnl_pct': pos['pnl_pct'],
            })

        return advices


# ==================== 命令行测试 ====================

if __name__ == '__main__':
    import sys

    tracker = PositionTracker()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'positions':
            positions = tracker.get_current_positions()
            if not positions:
                print("当前无持仓")
            else:
                total_cost = 0.0
                print(f"\n{'code':<15} {'名称':<12} {'买入日':<12} {'数量':<8} {'成本价':<8} {'市值':<10}")
                print('-' * 65)
                for p in positions:
                    cost = float(p['buy_price']) * float(p['quantity'])
                    total_cost += cost
                    print(f"{p['code']:<15} {p['name']:<12} {p['buy_date']:<12} "
                          f"{p['quantity']:<8} {p['buy_price']:<8} {cost:<10.2f}")
                print('-' * 65)
                print(f"{'总投入':>39} {total_cost:<10.2f}")

        elif cmd == 'history':
            rows = tracker.get_history()
            if not rows:
                print("无历史记录")
            else:
                print(f"\n{'ID':<4} {'code':<15} {'名称':<10} {'买入日':<12} {'卖出日':<12} "
                      f"{'数量':<6} {'盈亏':<10} {'状态':<6}")
                print('-' * 75)
                for r in rows:
                    pnl = r.get('pnl', '') or ''
                    print(f"{r['id']:<4} {r['code']:<15} {r['name']:<10} {r['buy_date']:<12} "
                          f"{r['sell_date']:<12} {r['quantity']:<6} {pnl:<10} {r['status']:<6}")
        else:
            print(f"未知命令: {cmd}")
            print("用法: python position_tracker.py [positions|history]")
    else:
        print(f"持仓文件: {tracker.csv_path}")
        positions = tracker.get_current_positions()
        print(f"当前持仓: {len(positions)} 笔")
        for p in positions:
            print(f"  [{p['type']}] {p['name']} ({p['code']}) "
                  f"{p['buy_date']} 买入 {p['quantity']} @ {p['buy_price']}")
