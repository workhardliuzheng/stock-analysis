import mysql.connector
from mysql.connector import Error
import yaml

class DatabaseManager:
    # 固定的配置文件路径
    CONFIG_FILE = 'config.yaml'

    def __init__(self):
        self.config = self.load_config()
        self.connection = None

    def load_config(self):
        """从固定路径加载配置文件"""
        with open(DatabaseManager.CONFIG_FILE, 'r') as file:
            config = yaml.safe_load(file)
        return config['database']

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.config['host'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password']
            )
            if self.connection.is_connected():
                print("数据库连接成功")
        except Error as e:
            print(f"Error: {e}")

    def disconnect(self):
        if self.connection.is_connected():
            self.connection.close()
            print("数据库连接已关闭")

    def insert(self, table, data):
        try:
            cursor = self.connection.cursor()
            placeholders = ', '.join(['%s'] * len(data))
            columns = ', '.join(data.keys())
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            cursor.execute(query, tuple(data.values()))
            self.connection.commit()
            print("数据插入成功")
        except Error as e:
            print(f"Error: {e}")

    def delete(self, table, condition):
        try:
            cursor = self.connection.cursor()
            query = f"DELETE FROM {table} WHERE {condition}"
            cursor.execute(query)
            self.connection.commit()
            print("数据删除成功")
        except Error as e:
            print(f"Error: {e}")

    def update(self, table, data, condition):
        try:
            cursor = self.connection.cursor()
            set_clause = ', '.join([f"{key} = %s" for key in data.keys()])
            query = f"UPDATE {table} SET {set_clause} WHERE {condition}"
            cursor.execute(query, tuple(data.values()))
            self.connection.commit()
            print("数据更新成功")
        except Error as e:
            print(f"Error: {e}")

    def select(self, table, columns='*', condition=None):
        try:
            cursor = self.connection.cursor()
            query = f"SELECT {columns} FROM {table}"
            if condition:
                query += f" WHERE {condition}"
            cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Error as e:
            print(f"Error: {e}")
            return None


