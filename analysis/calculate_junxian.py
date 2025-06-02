import pandas as pd
from sqlalchemy import create_engine

# 数据库连接配置
db_config = {
    'user': 'your_username',
    'password': 'your_password',
    'host': 'localhost',
    'database': 'your_database'
}

# 创建数据库引擎
engine = create_engine(f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@{db_config['host']}/{db_config['database']}")

# 从数据库中读取数据
query = "SELECT * FROM fund_data ORDER BY trade_date"
df = pd.read_sql(query, engine)

# 确保 trade_date 是日期时间类型
df['trade_date'] = pd.to_datetime(df['trade_date'])

# 计算均线
df['m5'] = df['close'].rolling(window=5).mean()
df['m10'] = df['close'].rolling(window=10).mean()
df['m20'] = df['close'].rolling(window=20).mean()
df['m60'] = df['close'].rolling(window=60).mean()
df['m120'] = df['close'].rolling(window=120).mean()

# 更新数据库中的数据
update_query = """
UPDATE fund_data
SET m5 = %s,
    m10 = %s,
    m20 = %s,
    m60 = %s,
    m120 = %s
WHERE id = %s
"""

with engine.connect() as connection:
    for index, row in df.iterrows():
        connection.execute(
            update_query,
            (row['m5'], row['m10'], row['m20'], row['m60'], row['m120'], row['id'])
        )

print("均值已成功计算并更新到数据库中")