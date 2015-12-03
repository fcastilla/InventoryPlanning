import csv
import math
import numpy as np
from Parameters import Parameters as params
from DemandData import DemandData
from datetime import datetime


class ProblemData:
    # Constructor
    def __init__(self):
        self.demandDataList = []
        self.maxDemand = 0.0
        self.repositionDays = []
        self.readDatafile()
        self.forecast = [[0 for i in range(len(self.demandDataList))] for j in range(len(self.demandDataList))]

    # Reads data file
    def readDatafile(self):
        print "Reading input data..."
        with open('.\\..\\data\\data_mid.csv') as csvfile:
            reader = csv.DictReader(csvfile)
            for r in reader:
                date = datetime.strptime(r["Date"], "%d/%m/%Y")
                demand = float(r["Sales"])
                self.maxDemand = max(self.maxDemand, demand)
                self.demandDataList.append(DemandData(date, demand))

        # Sort the data by date
        self.demandDataList.sort(key=lambda d: d.date)

    # Returns the stock to be considered at the begining of the scenario
    def getInitialStock(self):
        totalStock = 0
        initDay = params.initialDay
        lastDay = initDay + params.initialStockDays

        for i in range(initDay, lastDay):
            totalStock += self.demandDataList[i].demand

        return totalStock

    def setRepositionDays(self, days=[]):
        if len(days) > 0:
            self.repositionDays = days
            return

        for i in range(params.initialDay, len(self.demandDataList), params.repositionInterval):
            self.repositionDays.append(i)

    def computeForecast(self, t0):
        t = t0
        for d in self.demandDataList[t0:]:
            # get the real demand
            realDemand = d.demand

            # get error interval
            uncertainty = self.getCurrentUncertaintyInterval(t0,t)

            # raffle a demand error inside the error interval
            error = 0
            if uncertainty > 0:
                error = np.random.normal(0, uncertainty)

            # compute the demand forecast for t on this iteration (day)
            fDemand = realDemand + error
            self.forecast[t0][t] = fDemand

            t += 1

    def getForecast(self, t0, t):
        return self.forecast[t0][t]

    def getCurrentUncertaintyInterval(self, t0, t):
        return float(params.currentUncertainty * math.sqrt(t-t0))


