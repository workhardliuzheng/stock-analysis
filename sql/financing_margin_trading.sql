CREATE TABLE financing_margin_trading (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    trade_date VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '交易日期',
    exchange_id VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '交易所代码（SSE上交所SZSE深交所BSE北交所）',
    rzye FLOAT DEFAULT NULL COMMENT '融资余额(元)',
    rzmre FLOAT DEFAULT NULL COMMENT '融资买入额(元)',
    rzche FLOAT DEFAULT NULL COMMENT '融资偿还额(元)',
    rqye FLOAT DEFAULT NULL COMMENT '融券余额(元)',
    rqmcl FLOAT DEFAULT NULL COMMENT '融券卖出量(股,份,手)',
    rzrqye FLOAT DEFAULT NULL COMMENT '融资融券余额(元)',
    rqyl FLOAT DEFAULT NULL COMMENT '融券余量(股,份,手)'
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT='融资融券交易数据表';


