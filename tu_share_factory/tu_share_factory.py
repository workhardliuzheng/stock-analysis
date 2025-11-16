import os

import tushare
import tushare as ts
import yaml

from entity import constant


class TuShareFactory():
    @staticmethod
    def build_api_client():
        token = os.getenv('TuShareToken')
        return ts.pro_api(token)