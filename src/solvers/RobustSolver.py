import cplex
import numpy as np

from src.inputdata.Parameters import Parameters as params
from src.inputdata.ProblemData import ProblemData as pdata
from src.solutiondata.ProblemSolution import ProblemSolution
from Variable import Variable


# IN THIS EXAMPLE WE ARE WORKING WITH JUST ONE STORE AND ONE PRODUCT
# 1 time instant = 1 day
# ToDo: parametrize time period discretization

class RobustSolver:
    def __init__(self):
        self.pData = pdata()
        self.currentDay = params.initialDay
        self.finalDay = self.currentDay + params.horizon
        self.initialStock = []  # the initial stock at each iteration
        self.repositions = []  # the amounts repositioned to stock for each day
        self.variables = {} # all model variables
        self.solutions = []  # solutions of all iterations
        self.lp = 0
        self.numCols = 0

    # Creates the linear program
    def createModel(self):
        self.createVariables()
        self.createConstraints()

    def createVariables(self):
        numVars = 0
        numVars += self.createTimeIndexedVariable("d", params.unitPrice)
        numVars += self.createTimeIndexedVariable("f", params.productAbscenceCost)
        numVars += self.createTimeIndexedVariable("r", params.unitCost, params.repositionInterval)
        numVars += self.createTimeIndexedVariable("s", params.unitStockageCost)
        numVars += self.createTimeIndexedVariable("yplus", 0.0, 1, 0.0, 1.0)
        numVars += self.createTimeIndexedVariable("yminus", 0.0, 1, 0.0, 1.0)
        numVars += self.createTimeIndexedVariable("pi", 0.0, params.robustInterval)  # 1 for each 'robust' period
        numVars += self.createTimeIndexedVariable("gamma")  # 1 for eac time instant
        print(str(numVars) + " variables created.")

    def createTimeIndexedVariable(self, name, coefficient=0.0, interval=1, lb=0.0, ub=100000):
        numVars = 0
        for i in range(self.currentDay, self.finalDay, interval):
            v = Variable()
            v.name = name + str(i)
            v.col = self.numCols
            v.instant = i
            v.period = self.getPeriod(i)
            self.variables[v.name] = v
            self.lp.variables.add(obj=[coefficient], lb=[lb], ub=[ub], names=[v.name])
            self.numCols += 1
            numVars += 1
        return numVars

    def getVariable(self, vname):
        if vname in self.variables:
            return self.variables[vname]
        return 0

    def createConstraints(self):
        numConst = 0;
        numConst += self.createInitialStockConstraint()
        numConst += self.createStockFlowConstraint()
        numConst += self.createDemandConstraint()

    def createInitialStockConstraint(self):
        v = self.variables["s" + str(self.currentDay)]
        mind = [v.col]
        mval = [1.0]
        mConstraint = cplex.SparsePair(ind=mind, val=mval)
        self.lp.linear_constraints.add(lin_expr=[mConstraint], senses=["E"],
                                       rhs=[self.pData.getInitialStock()], names=["initial_stock"])
        return 1

    def createStockFlowConstraint(self):
        numCons = 0
        # s_{t} + r_{t-1} + f_{t} - s_{t+1} - d_{t} = 0
        for t in range(self.currentDay, self.finalDay):
            mind =[]
            mval =[]

            s = self.getVariable("s" + str(t))
            s1 = self.getVariable("s" + str(t+1))
            d = self.getVariable("d" + str(t))
            f = self.getVariable("f" + str(t))
            r = self.getVariable("r" + str(t))

            mind.append(s.name)
            mval.append(1.0)
            mind.append(f.name)
            mval.append(1.0)
            mind.append(d.name)
            mval.append(-1.0)

            if s1 != 0:
                mind.append(s1.name)
                mval.append(-1.0)

            if r != 0:
                mind.append(r.name)
                mval.append(1.0)

            mConstraint = cplex.SparsePair(ind=mind, val=mval)
            self.lp.linear_constraints.add(lin_expr=[mConstraint],
                                        senses=["E"], rhs=[0.0],
                                        names=["stock_flow" + str(t)])
            numCons += 1

        return numCons

    def createDemandConstraint(self):
        numCons = 0
        # d_{t} - deviation(d_{t}) \times (yplus_{t} - yminus_{t}) = mean(d_{t})
        for t in range(self.currentDay, self.finalDay):
            mind = []
            mval = []

            demandData = self.pData.demandDataList[t]
            mean = demandData.demand
            deviation = float(demandData.deviation)

            # demand variable
            d = self.getVariable("d" + str(t))
            mind.append(d.name)
            mval.append(1.0)

            yminus = self.getVariable("yminus" + str(t))
            mind.append(yminus.name)
            mval.append(deviation)

            yplus = self.getVariable("yplus" + str(t))
            mind.append(yplus.name)
            mval.append(-deviation)

            mConstraint = cplex.SparsePair(ind=mind, val=mval)
            self.lp.linear_constraints.add(lin_expr=[mConstraint],
                                        senses=["E"], rhs=[mean],
                                        names=["c_demand" + str(t)])
            numCons += 1

        return numCons

    def createRobustConstraint(self):
        print("ToDo")

    def getPeriod(self, i):
        return int(i / params.robustInterval)

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

    def test(self):
        #create lp
        self.lp = cplex.Cplex()
        self.lp.objective.set_sense(self.lp.objective.sense.maximize)
        # prob.set_log_stream(None)
        # prob.set_error_stream(None)
        # prob.set_warning_stream(None)
        # prob.set_results_stream(None)

        self.pData.calculateDemandForecast(self.currentDay)
        self.createModel()

        # write lp to file
        self.lp.write(".\\..\\lps\\robust_day_" + str(self.currentDay) + ".lp")
        self.lp.solve()

