import mysql.connector
import pandas as pd
from mysql.connector import Error
import yaml
from entity import constant

class DatabaseManager:
    # 固定的配置文件路径
    def __init__(self):
        self.config = self.load_config()
        self.connection = None

    def load_config(self):
        """从固定路径加载配置文件"""
        with open(constant.CONFIG_FILE, 'r', encoding='utf-8') as file:
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
                cursor = self.connection.cursor()
                cursor.execute("SET NAMES utf8mb4;")
                cursor.execute("SET CHARACTER SET utf8mb4;")
                cursor.execute("SET character_set_connection=utf8mb4;")
        except Error as e:
            print(f"Error: {e}")

    def disconnect(self):
        if self.connection.is_connected():
            self.connection.close()
            print("数据库连接已关闭")

    def insert(self, table, data):
        try:
            cursor = self.connection.cursor()

            # 创建占位符字符串，例如 '%s, %s, %s' 对应于三个值
            placeholders = ', '.join(['%s'] * len(data))
            # 获取列名并用逗号分隔，例如 'name, age, email'
            columns = ', '.join(data.keys())
            # 构建 SQL 插入查询
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

            # 执行查询并将字典的值作为参数传递
            cursor.execute(query, tuple(data.values()))
            # 提交事务
            self.connection.commit()
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

    def batch_insert(self, table, entities):
        if not entities:
            return

        # 获取第一个实体的字典以确定列名
        sample_data = entities[0].to_dict_with_backticks()
        columns = ', '.join(sample_data.keys())
        placeholders = ', '.join(['%s'] * len(sample_data))

        # 构建批量插入的SQL查询
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        try:
            cursor = self.connection.cursor()
            values = [tuple(entity.to_dict_with_backticks().values()) for entity in entities]
            cursor.executemany(query, values)
            self.connection.commit()
            print("批量数据插入成功")
        except Error as e:
            print(f"Error: {e}")

