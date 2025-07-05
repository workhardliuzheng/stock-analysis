ALTER TABLE ts_stock_data ADD UNIQUE KEY unique_ts_code_date (ts_code, trade_date);
ALTER TABLE market_data ADD UNIQUE KEY unique_ts_code_date (ts_code, trade_date);
ALTER TABLE fund_data ADD UNIQUE KEY unique_ts_code_date (ts_code, trade_date);
ALTER TABLE stock_weight ADD UNIQUE KEY unique_ts_code_date (ts_code, trade_date);

