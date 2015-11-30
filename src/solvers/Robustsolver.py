import cplex
import numpy as np
from Variable import Variable
from src.inputdata.Parameters import Parameters as params
from src.inputdata.ProblemData import ProblemData as pdata
from src.solutiondata.ProblemSolution import ProblemSolution


# IN THIS EXAMPLE WE ARE WORKING WITH JUST ONE STORE AND ONE PRODUCT
# 1 time instant = 1 day
# ToDo: parametrize time period discretization

class RobustSolver:
    def __init__(self, pData):
        self.pData = pData
        self.currentDay = params.initialDay
        self.finalDay = self.currentDay + params.horizon
        self.repositions = [0 for i in range(0, len(pData.demandDataList))]  # the amounts repositioned to stock for each day
        self.initialStock = [0 for i in range(0, len(pData.demandDataList))]  # the initial stock at each iteration
        self.initialStock[params.initialDay] = pData.getInitialStock()
        self.lp = 0
        self.variables = {}
        self.numCols = 0
        self.problemSolution = 0

    # Creates the linear program
    def createModel(self):
        self.lp.objective.set_sense(self.lp.objective.sense.maximize)
        self.createVariables()
        self.createConstraints()

    #region Variable Creation
    def createVariables(self):
        numVars = 0
        numVars += self.createDemandVariable()
        numVars += self.createRepositionVariable()
        numVars += self.createTimeIndexedVariable("f", Variable.v_fault, -params.productAbscenceCost)
        numVars += self.createTimeIndexedVariable("s", Variable.v_stock, -params.unitStockageCost)

    def createDemandVariable(self):
        numVars = 0
        for i in range(self.currentDay, self.finalDay):
            v = Variable()
            v.name = "d" + str(i)
            v.col = self.numCols
            v.instant = i
            v.type = Variable.v_demand
            demand = self.pData.demandDataList[i].robustDemand
            self.variables[v.name] = v
            self.lp.variables.add(obj=[params.unitPrice], lb=[demand], ub=[demand], names=[v.name])
            self.numCols += 1
            numVars += 1
        return numVars

    def createRepositionVariable(self):
        numVars = 0
        repositionDays = [rDay for rDay in self.pData.repositionDays if rDay < self.finalDay]

        for i in repositionDays:
            v = Variable()
            v.name = "r" + str(i)
            v.col = self.numCols
            v.instant = i
            v.type = Variable.v_demand
            maxReposition = self.pData.maxRobustDemand
            self.variables[v.name] = v
            self.lp.variables.add(obj=[-params.unitCost], ub=[maxReposition], names=[v.name])
            self.numCols += 1
            numVars += 1
        return numVars

    def createTimeIndexedVariable(self, name, v_type, coefficient=0.0, interval=1, lb=0.0, ub=1000000):
        numVars = 0
        for i in range(self.currentDay, self.finalDay, interval):
            v = Variable()
            v.name = name + str(i)
            v.col = self.numCols
            v.instant = i
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
        self.createConstraint(mind,mval,"E",self.initialStock[self.currentDay],"initial_stock")
        return 1

    def createStockFlowConstraint(self):
        numCons = 0
        # s_{t} + r_{t-1} + f_{t} - s_{t+1} = d_{t}
        for t in range(self.currentDay, self.finalDay):
            mind =[]
            mval =[]
            rhs = 0.0

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
            elif (t-1) > 0:
                rhs -= self.repositions[t-1]

            self.createConstraint(mind,mval,"E",rhs,"stock_flow" + str(t))
            numCons += 1

        return numCons

    def createConstraint(self, mind, mval, sense, rhs, name):
        mConstraint = cplex.SparsePair(ind=mind, val=mval)
        self.lp.linear_constraints.add(lin_expr=[mConstraint],
                                    senses=[sense], rhs=[rhs],
                                    names=[name])
    #endregion

    def reset(self):
        self.lp = 0
        self.variables = {}
        self.numCols = 0

    def createLp(self):
        self.reset()
        self.lp = cplex.Cplex()
        self.lp.set_log_stream(None)
        self.lp.set_error_stream(None)
        self.lp.set_warning_stream(None)
        self.lp.set_results_stream(None)
        self.createModel()

    def solve(self, day, maxIterations=1):
        self.currentDay = day
        self.finalDay = self.currentDay + params.horizon

        # begin the iterative procedure
        iterations = 0
        minVal = 100000000000000
        try:
            while iterations < maxIterations:
                # create lp
                self.createLp()

                # write the lp
                self.lp.write(".\\..\\lps\\robusto_day" + str(self.currentDay) + "_iter" + str(iterations) + ".lp")

                # solve the model
                self.lp.solve()

                # process solution, get stock reposition for current day and stock for next planning day
                solution = self.lp.solution
                objValue = solution.get_objective_value()
                x = solution.get_values()

                # check if we need to update the current "worst" solution
                if objValue < minVal:
                    # update worst solution value
                    minVal = objValue

                    # process solution
                    for k,v in self.variables.iteritems():
                        # load the reposition and stock quantity
                        col = v.col
                        t = v.instant
                        solVal = x[col]

                        if v.type == Variable.v_reposition:
                            self.repositions[t] = solVal
                        elif v.type == Variable.v_stock:
                            self.initialStock[t] = solVal

                    # store solution
                    self.problemSolution = ProblemSolution(self.currentDay,
                                                           self.repositions[self.currentDay], objValue)

                # recalculate robust demand for next iteration
                self.pData.calculateDemandForecast(self.currentDay)
                iterations += 1

        except:
            print "Error on t" + str(self.currentDay)
            raise

        return self.problemSolution
