import numpy as np

from mysql_connect.database_manager import DatabaseManager


class CommonMapper:

    def __init__(self, table_name):
        self.table_name = table_name
    def insert_base_entity(self, base_entity):
        database_manager = DatabaseManager()
        database_manager.connect()
        database_manager.insert(self.table_name, base_entity.to_dict_with_backticks(contains_id=False))
        database_manager.disconnect()

    def batch_insert_base_entity(self, base_entity_list):
        database_manager = DatabaseManager()
        database_manager.connect()
        database_manager.batch_insert(self.table_name, base_entity_list)
        database_manager.disconnect()

    def upsert_base_entities_batch(self, base_entity_list):
        database_manager = DatabaseManager()
        database_manager.connect()
        database_manager.upsert_base_entities_batch(self.table_name, base_entity_list)
        database_manager.disconnect()

    def select_base_entity(self, columns, condition):
        database_manager = DatabaseManager()
        database_manager.connect()
        result = database_manager.select(table=self.table_name, columns=columns, condition=condition)
        database_manager.disconnect()
        return result

    def update_base_entity(self, base_entity, columns, condition_columns):
        database_manager = DatabaseManager()
        entity_dict = base_entity.to_dict()

        extracted_data = {}
        condition_parts = []
        for key in entity_dict.keys():
            if key in columns:
                extracted_data[key] = nan_to_null(entity_dict[key])
            if key in condition_columns:
                value = entity_dict[key]
                condition_part = f"{key}={value}"
                condition_parts.append(condition_part)
        condition_string = " and ".join(condition_parts)

        database_manager.connect()
        database_manager.update(self.table_name, extracted_data, condition_string)
        database_manager.disconnect()

def nan_to_null(value):
    if np.isnan(value):
        return None
    return value
