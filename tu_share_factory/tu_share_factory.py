import tushare
import tushare as ts
import yaml

from entity import content


class TuShareFactory():
    @staticmethod
    def build_api_client():
        with open(content.CONFIG_FILE, 'r') as file:
            config = yaml.safe_load(file)
        token = config['token']
        return ts.pro_api(token)