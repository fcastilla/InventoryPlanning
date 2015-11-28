import csv
import math
import numpy as np
import random
from Parameters import Parameters as params
from DemandData import DemandData
from datetime import datetime


class ProblemData:
    # Constructor
    def __init__(self):
        self.demandDataList = []
        self.pessimismValues = []
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
        y = []
        sum = 0
        for i in range(0, params.horizon):
            y.append(np.random.uniform(-1,1))
            sum += math.fabs(y[i])

        for i in range(0, params.horizon):
            y[i] *= (params.defaultPessimism / sum)

        initialDemandData = self.demandDataList[t0]
        for t in range(t0, t0 + params.horizon):
            demandData = self.demandDataList[t]

            deviation = (demandData.demand * float(0.05*math.sqrt(t-t0))) - demandData.demand;
            lb = demandData.demand - deviation
            ub = demandData.demand + deviation
            #demandData.forecastDemand = np.random.uniform(ub,ub)

            demandData.forecastDemand = max(0, demandData.demand + (deviation * y[t]))

            # lb = demandData.demand * (1 - (0.05*(t-t0)))
            # ub = demandData.demand * (1 + (0.05*(t-t0)))
            # error = 0
            # if (initialDemandData.demand > 0):
            #     error = np.random.normal(0, initialDemandData.demand / 10)
            # demandData.forecastDemand = max(0, np.random.uniform(lb,ub) + error)

    def getPessimism(self,period):
        return params.defaultPessimism