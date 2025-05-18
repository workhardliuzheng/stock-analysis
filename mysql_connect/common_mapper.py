from mysql_connect.database_manager import DatabaseManager


class CommonMapper:

    def __init__(self, table_name):
        self.table_name = table_name
    def insert_base_entity(self, base_entity):
        database_manager = DatabaseManager()
        database_manager.connect()
        database_manager.insert(self.table_name, base_entity.to_dict_with_backticks(contains_id=False))
        database_manager.disconnect()

    def select_base_entity(self, columns, condition):
        database_manager = DatabaseManager()
        database_manager.connect()
        database_manager.select(table=self.table_name, columns=columns, condition=condition)
        database_manager.disconnect()

