class DemandData:
    def __init__(self, date, demand):
        self.date = date
        self.demand = demand

    def __repr__(self):
        return repr((self.date, self.realDemand, self.forecastDemand))
