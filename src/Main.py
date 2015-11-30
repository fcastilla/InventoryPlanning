from src.solvers.RobustSolver import RobustSolver
from src.solvers.DeterministicSolver import DeterministicSolver
from src.inputdata.ProblemData import ProblemData
from src.inputdata.Parameters import Parameters as params
from datetime import datetime
import numpy as np

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
                for t in range(self.initialDay, self.finalDay):
                    self.data.calculateDemandForecast(t)

                    print "Running deterministic solver for day " + str(t) + "(u=" + str(u) + " r=" + str(r) + ")"
                    dSolver = DeterministicSolver(self.data)
                    dSolution = dSolver.solve(t)

                    print "Running robust solver for day " + str(t) + "(u=" + str(u) + " r=" + str(r) + ")"
                    rSolver = RobustSolver(self.data)
                    rSolution = rSolver.solve(t,500)

                    self.printToFile(t,u,r,dSolution,rSolution)

    def printToFile(self, day, uncertainty, robustness, dSolution, rSolution):
        fileName = ".\\..\\output\\Inventory_u" + str(uncertainty).replace(".","") + "_r" + str(robustness).replace(".","") + ".csv"
        line = str(day) + "," + str(dSolution.objVal) + "," +  str(dSolution.reposition) + ","
        line += str(rSolution.objVal) + "," + str(rSolution.reposition) + "\n"
        f = open(fileName, "a")
        f.write(line)
        f.closed


planner = InventoryPlanner()
planner.executePlanning()