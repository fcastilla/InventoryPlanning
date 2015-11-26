import csv
import numpy as np
from Parameters import Parameters
from DemandData import DemandData
from datetime import datetime


class ProblemData:
    # Constructor
    def __init__(self):
        self.demandDataList = []
        self.readDatafile()

    # Reads data file
    def readDatafile(self):
        with open('data\\data_small.csv') as csvfile:
            reader = csv.DictReader(csvfile)
            for r in reader:
                date = datetime.strptime(r["Date"], "%d/%m/%Y")
                demand = float(r["Sales"])
                self.demandDataList.append(DemandData(date, demand))

        # Sort the data by date
        self.demandDataList.sort(key=lambda d: d.date)

    # Returns the real demand for any given day
    def getRealDemand(self, t):
        if t<0 or t>len(self.demandDataList):
            return 0

        return self.demandDataList[t].demand

    # Returns the forecast demand for a given day
    def getForecastDemand(self, t, t0):
        if t0 < 0 or t >= len(self.demandDataList):
            return 0

        d0 = self.demandDataList[t0]
        d1 = self.demandDataList[t]

        lb = d1.demand * (1 - (0.05 * (t - t0)))
        ub = d1.demand * (1 + (0.05 * (t - t0)))

        error = 0
        if d0.demand > 0:
            error = np.random.normal(0, d0.demand / 10)

        forecastDemand = max(0, np.random.uniform(lb, ub) + error)

        return forecastDemand

    # Returns the stock to be considered at the begining of the scenario
    def getInitialStock(self):
        totalStock = 0
        initDay = Parameters.initialDay
        lastDay = initDay + Parameters.initialStockDays

        for i in range(initDay, lastDay):
            totalStock += self.demandDataList[i].realDemand

        return totalStock
