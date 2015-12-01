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
        self.maxDemand = 0.0
        self.maxDemandForecast = 0.0
        self.y = []
        self.repositionDays = []
        self.readDatafile()

    # Reads data file
    def readDatafile(self):
        print "Reading input data..."
        with open('.\\..\\data\\data_mid.csv') as csvfile:
            reader = csv.DictReader(csvfile)
            for r in reader:
                date = datetime.strptime(r["Date"], "%d/%m/%Y")
                demand = float(r["Sales"])
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

    def calculateY(self):
        self.y = []

        # For each day of each period, calculate y
        # The sum of all y for a given period must be equal to the pessimism (robustness) parameter
        totalPeriods = int(math.ceil(float(params.horizon) / params.robustInterval))

        for p in range(totalPeriods):
            sum = 0
            for d in range(0,params.robustInterval):
                currentY = np.random.uniform(-1,1)
                self.y.append(currentY)
                sum += math.fabs(currentY)

            for d in range(0, params.robustInterval):
                day = (params.robustInterval * p) + d
                self.y[day] *= (params.currentRobustness / sum)

    # Calculates the 'fake' forecast demand for all days
    # based on an initial day given real demand
    def calculateDemandForecast(self, t0):
        self.calculateY()
        yIdx = 0
        initialDemandData = self.demandDataList[t0]
        for t in range(t0, t0 + params.horizon):
            demandData = self.demandDataList[t]
            uncertainty = float(params.currentUncertainty * math.sqrt(t-t0))

            # maximum deviation
            deviation = max(0, demandData.demand * uncertainty)
            demandData.deviation = deviation

            # additional error
            error = 0
            #error = np.random.normal(0, initialDemandData.demand / 10)

            # robust demand
            demandData.forecastDemand = max(0, demandData.demand + (deviation * self.y[yIdx]) + error)

            self.maxDemandForecast = max(self.maxDemandForecast, demandData.forecastDemand)
            self.maxDemand = max(self.maxDemand, demandData.demand)

            yIdx += 1

    def getPessimism(self,period):
        return params.defaultPessimism

    def setRepositionDays(self, days=[]):
        if len(days) > 0:
            self.repositionDays = days
            return

        for i in range(params.initialDay, len(self.demandDataList), params.repositionInterval):
            self.repositionDays.append(i)