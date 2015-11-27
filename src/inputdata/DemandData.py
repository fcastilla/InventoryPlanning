class DemandData:
    def __init__(self, date, demand):
        self.date = date
        self.demand = demand
        self.forecastDemand = 0
        self.deviation = 0.0

    def __repr__(self):
        return str(self.demand) + "/" +  str(self.forecastDemand) + "/" + str(self.deviation)
