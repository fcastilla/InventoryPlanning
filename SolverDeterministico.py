import numpy as np
import cplex
from ProblemData import ProblemData
from Parameters import Parameters
from ProblemSolution import ProblemSolution

# IN THIS EXAMPLE WE ARE WORKING WITH JUST ONE STORE AND ONE PRODUCT
# 1 time instant = 1 day
# ToDo: parametrize time period discretization

class DeterministicSolver:

    def __init__(self):
        self.pData = ProblemData()
        self.p = Parameters
        self.currentDay = Parameters.initialDay
        self.initialStock = []  # the initial stock at each iteration
        self.repositions = []  # the amounts repositioned to stock for each day
        self.vNames = []  # all variable names
        self.solutions = []  # solutions of all iterations

    # Creates the linear program
    def createModel(self, prob):
        p = self.p
        pData = self.pData
        currentDay = self.currentDay

        # set problem sense
        prob.objective.set_sense(prob.objective.sense.maximize)

        # ================
        # Create Variables
        # ================
        # Create a continuous f variable for each day
        fVarNames = ["f" + str(t) for t in range(currentDay, currentDay + p.horizon)]
        fVarObj = [-p.unitPrice] * p.horizon
        fVarUB = [d.demand for d in pData.demandDataList[currentDay:currentDay + p.horizon]]
        prob.variables.add(obj=fVarObj, ub=fVarUB, names=fVarNames)

        # Create a continuous r variable for each day
        rVarNames = ["r" + str(t) for t in range(currentDay, currentDay + p.horizon)]
        rVarObj = [-p.unitCost] * p.horizon
        prob.variables.add(obj=rVarObj, names=rVarNames)

        # Create a continuous s variable for each day but the first one (t0)
        sVarNames = ["s" + str(t) for t in range(currentDay + 1, currentDay + p.horizon + 1)]
        sVarObj = [-p.unitStockageCost] * (p.horizon)
        prob.variables.add(obj=sVarObj, names=sVarNames)

        self.vNames = fVarNames + rVarNames + sVarNames
        sVarNames.insert(0, "s" + str(currentDay))  # for indices to match names
        # ================

        # ==================
        # Create Constraints
        # ==================

        # Stock flow? contraint
        for t in range(currentDay, currentDay + p.horizon):
            # s_{t} + r_{t-1} + f_{t} - s_{t+1} = d_{t}
            mInd = []
            mVal = []
            demand = pData.getForecastDemand(currentDay, t)

            if (t - 1) >= currentDay:
                # the reposition variable should exist, so add it
                mInd.append("r" + str(t - 1))
                mVal.append(1.0)
            elif (currentDay - 1) >= 0:
                # obtain historical stock reposition value
                demand -= self.repositions[currentDay - 1]

            if t < (currentDay + p.horizon):
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
        self.currentDay = self.p.initialDay
        self.repositions = [0 for i in range(0, len())]
        initialStock = [0 for i in range(0, len(demandDataList))]
        initialStock[currentDay] = getInitialStock()

        # begin the iterative procedure
        iterations = 0
        try:
            while iterations < horizon:
                np.random.seed(iterations)

                # Forecast demand for current t
                forecastDemand()

                # create lp
                prob = cplex.Cplex()
                prob.set_log_stream(None)
                prob.set_error_stream(None)
                prob.set_warning_stream(None)
                prob.set_results_stream(None)
                createModel(prob)

                # write the lp and solve the model
                prob.write("test" + str(currentDay) + ".lp")
                prob.solve()

                # process solution, get stock reposition for current day and stock for next planning day
                solution = prob.solution
                x = solution.get_values()

                for i in range(len(x)):
                    # load the reposition and stock quantity
                    varName = vNames[i]
                    varType = varName[:1]
                    t = int(varName[1:])

                    if varType == "r":
                        repositions[t] = x[i]
                    elif varType == "s":
                        initialStock[t] = x[i]

                solutions.append(ProblemSolution(demandDataList, repositions, initialStock))

                currentDay += 1
                iterations += 1
        except:
            print "Error on t" + str(currentDay)
            raise
