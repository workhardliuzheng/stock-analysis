CREATE TABLE `market_data` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键',
  `trade_date` datetime DEFAULT NULL COMMENT '交易日期',
  `ts_code` varchar(255) DEFAULT NULL COMMENT '市场代码',
  `ts_name` varchar(255) DEFAULT NULL COMMENT '市场名称',
  `com_count` int(11) DEFAULT NULL COMMENT '挂牌数',
  `total_share` float(20,4) DEFAULT NULL COMMENT '总股本（亿股）',
  `float_share` float(20,4) DEFAULT NULL COMMENT '流通股本（亿股）',
  `total_mv` float(20,4) DEFAULT NULL COMMENT '总市值（亿元）',
  `float_mv` float(20,4) DEFAULT NULL COMMENT '流通市值（亿元）',
  `amount` float(20,4) DEFAULT NULL COMMENT '交易金额（亿元）',
  `vol` float(20,4) DEFAULT NULL COMMENT '成交量（亿股）',
  `trans_count` int(11) DEFAULT NULL COMMENT '成交笔数（万笔）',
  `pe` float(20,4) DEFAULT NULL COMMENT '平均市盈率',
  `tr` float(20,4) DEFAULT NULL COMMENT '换手率（％）',
  `exchange` varchar(255) DEFAULT NULL COMMENT '交易所',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3001 DEFAULT CHARSET=utf8mb4