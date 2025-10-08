from entity.base_entity import BaseEntity

class FinancingMarginTrading(BaseEntity):
    def __init__(self, id=None, trade_date=None, exchange_id=None, rzye=None,
                 rzmre=None, rzche=None, rqye=None, rqmcl=None, rzrqye=None, rqyl=None):
        self.id = id
        self.trade_date = trade_date
        self.exchange_id = exchange_id
        self.rzye = rzye
        self.rzmre = rzmre
        self.rzche = rzche
        self.rqye = rqye
        self.rqmcl = rqmcl
        self.rzrqye = rzrqye
        self.rqyl = rqyl

    # Getter methods for each field
    def get_id(self):
        return self.id

    def get_trade_date(self):
        return self.trade_date

    def get_exchange_id(self):
        return self.exchange_id

    def get_rzye(self):
        return self.rzye

    def get_rzmre(self):
        return self.rzmre

    def get_rzche(self):
        return self.rzche

    def get_rqye(self):
        return self.rqye

    def get_rqmcl(self):
        return self.rqmcl

    def get_rzrqye(self):
        return self.rzrqye

    def get_rqyl(self):
        return self.rqyl

    # Setter methods for each field
    def set_id(self, id):
        self.id = id

    def set_trade_date(self, trade_date):
        self.trade_date = trade_date

    def set_exchange_id(self, exchange_id):
        self.exchange_id = exchange_id

    def set_rzye(self, rzye):
        self.rzye = rzye

    def set_rzmre(self, rzmre):
        self.rzmre = rzmre

    def set_rzche(self, rzche):
        self.rzche = rzche

    def set_rqye(self, rqye):
        self.rqye = rqye

    def set_rqmcl(self, rqmcl):
        self.rqmcl = rqmcl

    def set_rzrqye(self, rzrqye):
        self.rzrqye = rzrqye

    def set_rqyl(self, rqyl):
        self.rqyl = rqyl


