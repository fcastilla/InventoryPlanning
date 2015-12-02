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

    def getPessimism(self,period):
        return params.defaultPessimism

    def setRepositionDays(self, days=[]):
        if len(days) > 0:
            self.repositionDays = days
            return

        for i in range(params.initialDay, len(self.demandDataList), params.repositionInterval):
            self.repositionDays.append(i)