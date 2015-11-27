import cplex
import numpy as np

from src.inputdata.Parameters import Parameters as params
from src.inputdata.ProblemData import ProblemData as pdata
from src.solutiondata.ProblemSolution import ProblemSolution


# IN THIS EXAMPLE WE ARE WORKING WITH JUST ONE STORE AND ONE PRODUCT
# 1 time instant = 1 day
# ToDo: parametrize time period discretization

class DeterministicSolver:
    def __init__(self):
        self.pData = pdata()
        self.currentDay = params.initialDay
        self.initialStock = []  # the initial stock at each iteration
        self.repositions = []  # the amounts repositioned to stock for each day
        self.vNames = []  # all variable names
        self.solutions = []  # solutions of all iterations

    # Creates the linear program
    def createModel(self, prob):
        pData = self.pData
        currentDay = self.currentDay

        # set problem sense
        prob.objective.set_sense(prob.objective.sense.maximize)

        # ================
        # Create Variables
        # ================
        # Create a continuous f variable for each day
        fVarNames = ["f" + str(t) for t in range(currentDay, currentDay + params.horizon)]
        fVarObj = [-params.productAbscenceCost] * params.horizon
        fVarUB = [d.demand for d in pData.demandDataList[currentDay:currentDay + params.horizon]]
        prob.variables.add(obj=fVarObj, ub=fVarUB, names=fVarNames)

        # Create a continuous r variable for each day
        rVarNames = ["r" + str(t) for t in range(currentDay, currentDay + params.horizon)]
        rVarObj = [-params.unitCost] * params.horizon
        prob.variables.add(obj=rVarObj, names=rVarNames)

        # Create a continuous s variable for each day but the first one (t0)
        sVarNames = ["s" + str(t) for t in range(currentDay + 1, currentDay + params.horizon + 1)]
        sVarObj = [-params.unitStockageCost] * (params.horizon)
        prob.variables.add(obj=sVarObj, names=sVarNames)

        self.vNames = fVarNames + rVarNames + sVarNames
        sVarNames.insert(0, "s" + str(currentDay))  # for indices to match names
        # ================

        # ==================
        # Create Constraints
        # ==================

        # Stock flow? contraint
        for t in range(currentDay, currentDay + params.horizon):
            # s_{t} + r_{t-1} + f_{t} - s_{t+1} = d_{t}
            mInd = []
            mVal = []
            demand = pData.demandDataList[t].forecastDemand

            if (t - 1) >= currentDay:
                # the reposition variable should exist, so add it
                mInd.append("r" + str(t - 1))
                mVal.append(1.0)
            elif (currentDay - 1) >= 0:
                # obtain historical stock reposition value
                demand -= self.repositions[currentDay - 1]

            if t < (currentDay + params.horizon):
                mInd.append("s" + str(t + 1))
                mVal.append(-1.0)

            if t > currentDay:
                mInd.append("s" + str(t))
                mVal.append(1.0)

            mInd.append("f" + str(t))
            mVal.append(1.0)

            if t == currentDay:
                demand -= self.initialStock[currentDay]

            mConstraint = cplex.SparsePair(ind=mInd, val=mVal)
            prob.linear_constraints.add(lin_expr=[mConstraint],
                                        senses=["E"], rhs=[demand],
                                        names=["c_t" + str(t)])

            # ==================

    def solve(self):
        # set initial variables
        pData = self.pData

        self.currentDay = params.initialDay
        self.repositions = [0 for i in range(0, len(pData.demandDataList))]
        self.initialStock = [0 for i in range(0, len(pData.demandDataList))]
        self.initialStock[self.currentDay] = pData.getInitialStock()

        # begin the iterative procedure
        iterations = 0
        try:
            while iterations < params.horizon:
                np.random.seed(iterations)

                # calculate demand forecast
                pData.calculateDemandForecast(self.currentDay)

                # create lp
                prob = cplex.Cplex()
                # prob.set_log_stream(None)
                # prob.set_error_stream(None)
                # prob.set_warning_stream(None)
                # prob.set_results_stream(None)
                self.createModel(prob)

                # write the lp and solve the model
                prob.write(".\\..\\lps\\test" + str(self.currentDay) + ".lp")
                prob.solve()

                # process solution, get stock reposition for current day and stock for next planning day
                solution = prob.solution
                x = solution.get_values()

                for i in range(len(x)):
                    # load the reposition and stock quantity
                    varName = self.vNames[i]
                    varType = varName[:1]
                    t = int(varName[1:])

                    if varType == "r":
                        self.repositions[t] = x[i]
                    elif varType == "s":
                        self.initialStock[t] = x[i]

                self.solutions.append(ProblemSolution(pData.demandDataList,
                                                      self.repositions, self.initialStock))

                self.currentDay += 1
                iterations += 1
        except:
            print "Error on t" + str(self.currentDay)
            raise

