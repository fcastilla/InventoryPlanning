from datetime import datetime

import numpy as np

from src.inputdata.Parameters import Parameters as params
from src.inputdata.ProblemData import ProblemData
from src.inputdata.Scenario import Scenario
from src.solvers.DeterministicSolver import DeterministicSolver
from src.solvers.RobustSolver import RobustSolver


class InventoryPlanner:
    def __init__(self):
        self.data = ProblemData()
        self.totalDays = len(self.data.demandDataList)
        self.initialDay = params.initialDay
        self.finalDay = self.initialDay + params.horizon
        self.date = datetime.now()
        np.random.seed(0)

    def runBatchExperiments(self):
        print "Starting inventory planning..."

        # Call both solvers, deterministic and robust for each planning day
        for u in params.uncertainties:
            params.currentUncertainty = u
            for r in params.robustness:
                params.currentRobustness = r
                self.run()

    def executePlanning(self):
        # initialize problem data
        self.data.setRepositionDays()

        # create solvers
        dSolver = DeterministicSolver(self.data)
        rSolver = RobustSolver(self.data)

        # solution arrays
        dRepositions = [0 for i in range(self.totalDays)]
        rRepositions = [0 for i in range(self.totalDays)]

        for t in range(self.initialDay, self.finalDay):
            # compute forecast for current day
            self.data.computeForecast(t)

            print "Running deterministic solver for day " + str(t)
            dRepositions[t] = dSolver.solve(t).reposition

            print "Running robust solver for day " + str(t)
            rRepositions[t] = rSolver.solve(t).reposition

            print "Day:", str(t), " | Det:", str(dRepositions[t]), " | Rob:", str(rRepositions[t])

        # Use obtained repositions to calculate stocks and faults at each day
        dFault = [0 for i in range(self.totalDays)]
        rFault = [0 for i in range(self.totalDays)]

        dStock = [0 for i in range(self.totalDays)]
        rStock = [0 for i in range(self.totalDays)]

        dStock[params.initialDay] = self.data.getInitialStock()
        rStock[params.initialDay] = self.data.getInitialStock()

        for t in range(self.initialDay, self.finalDay - 1):
            dStock[t+1] = dStock[t] - self.data.demandDataList[t].demand
            rStock[t+1] = rStock[t] - self.data.demandDataList[t].demand

            if t-1 > 0:
                dStock[t+1] += dRepositions[t-1]
                rStock[t+1] += rRepositions[t-1]

            if dStock[t+1] < 0:
                dFault[t+1] = dStock[t+1]
                dStock[t+1] = 0

            if rStock[t+1] < 0:
                rFault[t+1] = rStock[t+1]
                rStock[t+1] = 0

        # compute objective values for each solver
        dObj = [0 for i in range(self.totalDays)]
        rObj = [0 for i in range(self.totalDays)]

        for t in range(self.initialDay, self.finalDay):
            demand = self.data.demandDataList[t].demand
            dVal = (params.unitPrice*demand) - (params.productAbscenceCost*dFault[t]) - \
                   (params.unitCost*dRepositions[t]) - (params.unitStockageCost*dStock[t])
            rVal = (params.unitPrice*demand) - (params.productAbscenceCost*rFault[t]) - \
                   (params.unitCost*rRepositions[t]) - (params.unitStockageCost*rStock[t])

            if t == self.initialDay:
                dObj[t] = dVal
                rObj[t] = rVal
            else:
                dObj[t] = dObj[t-1] + dVal
                rObj[t] = rObj[t-1] + rVal

            self.printToFile(t, demand, dObj[t],dRepositions[t],rObj[t],rRepositions[t])

    def printToFile(self, day, realDemand, dObj, dRep, rObj, rRep):
        fileName = ".\\..\\output\\Inventory_u" + str(params.currentUncertainty).replace(".","") + \
                   "_r" + str(params.currentRobustness).replace(".","") + ".csv"

        line = str(day) + ";" + '{:.2f}'.format(realDemand).replace(".",",")  + ";" + '{:.2f}'.format(dObj).replace(".",",") + ";" \
               +  '{:.2f}'.format(dRep).replace(".",",") + ";" + '{:.2f}'.format(rObj).replace(".",",") + ";" \
               + '{:.2f}'.format(rRep).replace(".",",") + "\n"

        f = open(fileName, "a")
        f.write(line)
        f.close()


planner = InventoryPlanner()
planner.executePlanning()