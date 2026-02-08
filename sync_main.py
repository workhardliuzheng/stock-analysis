"""
数据同步入口

同步顺序说明：
1. 股票基础数据 - 其他同步依赖此数据
2. 两融数据
3. 权重数据
4. 收入数据
5. 财务数据
6. 股票日线数据
7. 指数数据 - 放在最后，因为指数计算依赖上述数据
"""
import argparse

from sync.stock.sync_stock_basic import StockBasicSync
from sync.stock.sync_stock_daily_basic import StockDailyBasicSync
from sync.stock.sync_financing_margin_trading import FinancingMarginTradingSync
from sync.index.sync_stock_weight import StockWeightSync
from sync.stock.sync_income import IncomeSync
from sync.stock.sync_financial_data import FinancialDataSync
from sync.index.sixty_index_analysis import SixtyIndexAnalysis


def sync_all(start_date='20200101'):
    """
    执行所有同步任务
    
    Args:
        start_date: 指数数据同步的开始日期
    """
    # 1. 同步股票基础数据（其他依赖此数据）
    print('=' * 50)
    print('1. 同步股票基础数据')
    print('=' * 50)
    StockBasicSync().sync_all()
    
    # 2. 同步两融数据
    print('=' * 50)
    print('2. 同步两融数据')
    print('=' * 50)
    FinancingMarginTradingSync().additional_data()
    
    # 3. 同步权重数据
    print('=' * 50)
    print('3. 同步权重数据')
    print('=' * 50)
    StockWeightSync().additional_data()
    
    # 4. 同步收入数据
    print('=' * 50)
    print('4. 同步收入数据')
    print('=' * 50)
    IncomeSync().additional_data()
    
    # 5. 同步财务数据
    print('=' * 50)
    print('5. 同步财务数据')
    print('=' * 50)
    FinancialDataSync().additional_data()
    
    # 6. 同步股票日线数据
    print('=' * 50)
    print('6. 同步股票日线数据')
    print('=' * 50)
    StockDailyBasicSync().sync_all()
    
    # 7. 同步指数数据（最后，依赖上述数据）
    print('=' * 50)
    print('7. 同步指数数据')
    print('=' * 50)
    SixtyIndexAnalysis().additional_data(start_date)
    
    print('=' * 50)
    print('所有数据同步完成！')
    print('=' * 50)


def sync_index_only(start_date='20200101'):
    """仅同步指数数据"""
    print('同步指数数据')
    SixtyIndexAnalysis().additional_data(start_date)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='股票分析系统 - 数据同步')
    parser.add_argument('--start-date', default='20200101', help='指数数据同步开始日期 (默认: 20200101)')
    parser.add_argument('--index-only', action='store_true', help='仅同步指数数据')
    args = parser.parse_args()
    
    if args.index_only:
        sync_index_only(args.start_date)
    else:
        sync_all(args.start_date)
