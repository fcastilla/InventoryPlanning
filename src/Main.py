from src.solvers.RobustSolver import RobustSolver
from src.solvers.DeterministicSolver import DeterministicSolver
from src.inputdata.ProblemData import ProblemData
from src.inputdata.Parameters import Parameters as params
from datetime import datetime
import numpy as np
import locale

class InventoryPlanner:
    def __init__(self):
        self.data = ProblemData()
        self.initialDay = params.initialDay
        self.finalDay = self.initialDay + params.horizon
        self.date = datetime.now()

    def executePlanning(self):
        print "Starting inventory planning..."

        # set the random generator seed
        np.random.seed(0)

        # initialize problem data
        self.data.setRepositionDays()

        # Call both solvers, deterministic and robust for each planning day
        for u in params.uncertainties:
            params.currentUncertainty = u
            for r in params.robustness:
                params.currentRobustness = r
                self.run()

    def run(self):
        # create solvers
        dSolver = DeterministicSolver(self.data)
        rSolver = RobustSolver(self.data)

        # solution arrays
        dRepositions = [0 for d in self.data.demandDataList]
        rRepositions = [0 for d in self.data.demandDataList]

        for t in range(self.initialDay, self.finalDay):
            print "Running deterministic solver for day " + str(t)
            dRepositions[t] = dSolver.solve(t).reposition

            print "Running robust solver for day " + str(t)
            rRepositions[t] = rSolver.solve(t).reposition

        # Use obtained repositions to calculate stocks and faults at each day
        dFault = [0 for d in self.data.demandDataList]
        rFault = [0 for d in self.data.demandDataList]

        dStock = [0 for d in self.data.demandDataList]
        rStock = [0 for d in self.data.demandDataList]

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
        dObj = [0 for d in self.data.demandDataList]
        rObj = [0 for d in self.data.demandDataList]

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

            self.printToFile(t,dObj[t],dRepositions[t],rObj[t],rRepositions[t])

    def printToFile(self, day, dObj, dRep, rObj, rRep):
        fileName = ".\\..\\output\\Inventory_u" + str(params.currentUncertainty).replace(".","") + \
                   "_r" + str(params.currentRobustness).replace(".","") + ".csv"

        line = str(day) + ";" + '{:.2f}'.format(dObj).replace(".",",") + ";" +  '{:.2f}'.format(dRep).replace(".",",") + ";"
        line += '{:.2f}'.format(rObj).replace(".",",") + ";" + '{:.2f}'.format(rRep).replace(".",",") + "\n"

        f = open(fileName, "a")
        f.write(line)
        f.closed


planner = InventoryPlanner()
planner.executePlanning()