CREATE TABLE `ts_stock_data` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '自动生成ID',
  `ts_code` varchar(255) DEFAULT NULL COMMENT '交易代码',
  `trade_date` datetime DEFAULT NULL COMMENT '交易日期',
  `close` float(20,4) DEFAULT NULL COMMENT '收盘价',
  `open` float(20,4) DEFAULT NULL COMMENT '开盘价',
  `high` float(20,4) DEFAULT NULL COMMENT '最高价',
  `low` float(20,4) DEFAULT NULL COMMENT '最低价',
  `pre_close` float(20,4) DEFAULT NULL COMMENT '前一收盘价',
  `change` float(20,4) DEFAULT NULL COMMENT '涨跌额',
  `pct_chg` float(20,4) DEFAULT NULL COMMENT '涨跌幅(%)',
  `vol` float(20,4) DEFAULT NULL COMMENT '成交量',
  `amount` float(20,4) DEFAULT NULL COMMENT '成交金额',
  `average_amount` float(20,4) DEFAULT NULL COMMENT '平均成交额',
  `deviation_rate` float(20,4) DEFAULT NULL COMMENT '偏离率',
  `name` varchar(255) DEFAULT NULL COMMENT '名称',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4