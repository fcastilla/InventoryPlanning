import cplex
import numpy as np
from Variable import Variable
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
        self.finalDay = self.currentDay + params.horizon
        self.initialStock = []  # the initial stock at each iteration
        self.repositions = []  # the amounts repositioned to stock for each day
        self.variables = {} # all model variables
        self.solutions = []  # solutions of all iterations
        self.lp = 0
        self.numCols = 0

    # Creates the linear program
    def createModel(self):
        self.lp.objective.set_sense(self.lp.objective.sense.maximize)
        self.createVariables()
        self.createConstraints()

    #region Variable Creation
    def createVariables(self):
        numVars = 0
        numVars += self.createDemandVariable()
        numVars += self.createTimeIndexedVariable("f", Variable.v_fault, -params.productAbscenceCost)
        numVars += self.createTimeIndexedVariable("r", Variable.v_reposition, -params.unitCost, params.repositionInterval)
        numVars += self.createTimeIndexedVariable("s", Variable.v_stock, -params.unitStockageCost)

    def createDemandVariable(self):
        numVars = 0
        for i in range(self.currentDay, self.finalDay):
            v = Variable()
            v.name = "d" + str(i)
            v.col = self.numCols
            v.instant = i
            v.period = int(i / params.robustInterval)
            v.type = Variable.v_demand
            demand = self.pData.demandDataList[i].forecastDemand
            self.variables[v.name] = v
            self.lp.variables.add(obj=[params.unitPrice], lb=[demand], ub=[demand], names=[v.name])
            self.numCols += 1
            numVars += 1
        return numVars

    def createTimeIndexedVariable(self, name, v_type, coefficient=0.0, interval=1, lb=0.0, ub=100000):
        numVars = 0
        for i in range(self.currentDay, self.finalDay, interval):
            v = Variable()
            v.name = name + str(i)
            v.col = self.numCols
            v.instant = i
            v.period = int(i / params.robustInterval)
            v.type = v_type
            self.variables[v.name] = v
            self.lp.variables.add(obj=[coefficient], lb=[lb], ub=[ub], names=[v.name])
            self.numCols += 1
            numVars += 1
        return numVars

    def getVariable(self, vname):
        if vname in self.variables:
            return self.variables[vname]
        return 0
    #endregion

    #region Constraint Creation
    def createConstraints(self):
        numConst = 0;
        numConst += self.createInitialStockConstraint()
        numConst += self.createStockFlowConstraint()

    def createInitialStockConstraint(self):
        v = self.variables["s" + str(self.currentDay)]
        mind = [v.col]
        mval = [1.0]
        self.createConstraint(mind,mval,"E",self.pData.getInitialStock(),"initial_stock")
        return 1

    def createStockFlowConstraint(self):
        numCons = 0
        # s_{t} + r_{t-1} + f_{t} - s_{t+1} = d_{t}
        for t in range(self.currentDay, self.finalDay):
            mind =[]
            mval =[]

            demand = self.pData.demandDataList[t].forecastDemand

            s = self.getVariable("s" + str(t))
            s1 = self.getVariable("s" + str(t+1))
            d = self.getVariable("d" + str(t))
            f = self.getVariable("f" + str(t))
            r = self.getVariable("r" + str(t-1))

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

            self.createConstraint(mind,mval,"E",0.0,"stock_flow" + str(t))
            numCons += 1

        return numCons

    def createConstraint(self, mind, mval, sense, rhs, name):
        mConstraint = cplex.SparsePair(ind=mind, val=mval)
        self.lp.linear_constraints.add(lin_expr=[mConstraint],
                                    senses=[sense], rhs=[rhs],
                                    names=[name])
    #endregion

    def solve(self):
        self.currentDay = params.initialDay
        self.currentPeriod = 0
        self.repositions = [0 for i in range(0, len(self.pData.demandDataList))]
        self.initialStock = [0 for i in range(0, len(self.pData.demandDataList))]
        self.initialStock[self.currentDay] = self.pData.getInitialStock()

        # begin the iterative procedure
        iterations = 0
        minVal = 100000000000000
        maxVal = -100000000000000
        try:
            while iterations < 1000:
                np.random.seed(iterations)

                # calculate demand forecast
                self.pData.calculateDemandForecast(self.currentDay)

                # create lp
                self.lp = cplex.Cplex()
                self.lp.set_log_stream(None)
                self.lp.set_error_stream(None)
                self.lp.set_warning_stream(None)
                self.lp.set_results_stream(None)
                self.createModel()

                # write the lp and solve the model
                # self.lp.write(".\\..\\lps\\deterministico_" + str(iterations) + ".lp")
                self.lp.solve()

                # process solution, get stock reposition for current day and stock for next planning day
                solution = self.lp.solution
                objValue = solution.get_objective_value()

                minVal = min(minVal, objValue)
                maxVal = max(maxVal, objValue)

                x = solution.get_values()

                # print "**********************************************"
                print "Deterministico - t" + str(self.currentDay) + " obj val: " + str(objValue)

                for k,v in self.variables.iteritems():
                    # load the reposition and stock quantity
                    col = v.col
                    t = v.instant
                    solVal = x[col]

                    # print v.name, "=", solVal

                    if v.type == Variable.v_reposition:
                        self.repositions[t] = solVal
                    elif v.type == Variable.v_stock:
                        self.initialStock[t] = solVal

                self.solutions.append(ProblemSolution(self.pData.demandDataList,
                                                      self.repositions, self.initialStock,objValue))

                #self.currentDay += 1
                self.variables = {}
                self.numCols = 0

                iterations += 1
        except:
            print "Error on t" + str(self.currentDay)
            raise

        print "Pior valor da fo:", minVal
        print "Melhor valor da fo:", maxVal