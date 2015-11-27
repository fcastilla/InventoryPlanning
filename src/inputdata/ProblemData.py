import csv
import numpy as np
from Parameters import Parameters as params
from DemandData import DemandData
from datetime import datetime


class ProblemData:
    # Constructor
    def __init__(self):
        self.demandDataList = []
        self.readDatafile()

    # Reads data file
    def readDatafile(self):
        with open('.\\..\\data\\data_small.csv') as csvfile:
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

    # Returns the stock to be considered at the begining of the scenario
    def getInitialStock(self):
        totalStock = 0
        initDay = params.initialDay
        lastDay = initDay + params.initialStockDays

        for i in range(initDay, lastDay):
            totalStock += self.demandDataList[i].demand

        return totalStock

    #Calculates the 'fake' forecast demand for all days
    #based on an initial day given real demand
    def calculateDemandForecast(self, t0):
        initialDemandData = self.demandDataList[t0]
        for t in range(t0, t0 + params.horizon):
            demandData = self.demandDataList[t]
            demandData.deviation = demandData.demand * float(0.05*(t-t0));
            lb = demandData.demand * (1 - (0.05*(t-t0)))
            ub = demandData.demand * (1 + (0.05*(t-t0)))
            error = 0
            if (initialDemandData.demand > 0):
                error = np.random.normal(0, initialDemandData.demand / 10)
            demandData.forecastDemand = max(0, np.random.uniform(lb,ub) + error)


