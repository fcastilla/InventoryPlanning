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

        # create solvers
        dSolver = DeterministicSolver(self.data)
        rSolver = RobustSolver(self.data)

        # Call both solvers, deterministic and robust for each planning day
        for u in params.uncertainties:
            params.currentUncertainty = u
            for r in params.robustness:
                params.currentRobustness = r
                for t in range(self.initialDay, self.finalDay):
                    self.data.calculateDemandForecast(t)

                    # print "Running deterministic solver for day " + str(t) + "(u=" + str(u) + " r=" + str(r) + ")"
                    dSolution = dSolver.solve(t)

                    # print "Running robust solver for day " + str(t) + "(u=" + str(u) + " r=" + str(r) + ")"
                    rSolution = rSolver.solve(t,500)

                    print "Results for day:", str(t), ":" ,dSolution.objVal, " | ", rSolution.objVal
                    self.printToFile(t,u,r,dSolution,rSolution)

    def printToFile(self, day, uncertainty, robustness, dSolution, rSolution):
        fileName = ".\\..\\output\\Inventory_u" + str(uncertainty).replace(".","") + "_r" + str(robustness).replace(".","") + ".csv"
        line = str(day) + ";" + '{:.2f}'.format(dSolution.objVal).replace(".",",") + ";" +  '{:.2f}'.format(dSolution.reposition).replace(".",",") + ";"
        line += '{:.2f}'.format(rSolution.objVal).replace(".",",") + ";" + '{:.2f}'.format(rSolution.reposition).replace(".",",") + "\n"
        f = open(fileName, "a")
        f.write(line)
        f.closed


planner = InventoryPlanner()
planner.executePlanning()