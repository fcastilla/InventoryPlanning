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
    def __init__(self, pData):
        self.pData = pData
        self.currentDay = params.initialDay
        self.finalDay = self.currentDay + params.horizon
        self.repositions = [0 for i in range(0, len(pData.demandDataList))]  # the amounts repositioned to stock for each day
        self.initialStock = [0 for i in range(0, len(pData.demandDataList))]  # the initial stock at each iteration
        self.plannedRepositions = [[0 for i in range(len(pData.demandDataList))] for t in range(params.horizon)]
        self.plannedStocks = [[0 for i in range(len(pData.demandDataList))] for t in range(params.horizon)]
        self.plannedFaults = [[0 for i in range(len(pData.demandDataList))] for t in range(params.horizon)]
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
        t0 = self.currentDay
        for t in range(self.currentDay, self.finalDay):
            v = Variable()
            v.name = "d" + str(t)
            v.col = self.numCols
            v.instant = t
            v.type = Variable.v_demand
            demand = self.pData.getForecast(t0, t)
            self.variables[v.name] = v
            self.lp.variables.add(obj=[params.unitPrice], lb=[demand], ub=[demand], names=[v.name])
            self.numCols += 1
            numVars += 1
        return numVars

    def createRepositionVariable(self):
        numVars = 0
        repositionDays = [rDay for rDay in self.pData.repositionDays if rDay >= self.currentDay and rDay < self.finalDay]

        for i in repositionDays:
            v = Variable()
            v.name = "r" + str(i)
            v.col = self.numCols
            v.instant = i
            v.type = Variable.v_reposition
            self.variables[v.name] = v
            self.lp.variables.add(obj=[-params.unitCost], names=[v.name])
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

    def computeInitialStock(self):
        t = self.currentDay
        if t == params.initialDay:
            self.initialStock[t] = self.pData.getInitialStock()
        else:
            self.initialStock[t] = self.initialStock[t-1] - self.pData.demandDataList[t-1].demand
            if t-params.currentLeadTime > 0:
                self.initialStock[t] += self.repositions[t-params.currentLeadTime]

        self.initialStock[t] = max(0, self.initialStock[t])

    def createInitialStockConstraint(self):
        # get the initial stock value for the current day, which will be the same for all scenarios.
        self.computeInitialStock()

        v = self.variables["s" + str(self.currentDay)]
        mind = [v.col]
        mval = [1.0]
        self.createConstraint(mind,mval,"E",self.initialStock[self.currentDay],"initial_stock")
        return 1

    def createStockFlowConstraint(self):
        numCons = 0
        # s_{t} + r_{t-1} + f_{t} - s_{t+1} = d_{t}
        for t in range(self.currentDay, self.finalDay-1):
            mind =[]
            mval =[]
            rhs = 0.0

            s = self.getVariable("s" + str(t))
            s1 = self.getVariable("s" + str(t+1))
            d = self.getVariable("d" + str(t))
            f = self.getVariable("f" + str(t))
            r = self.getVariable("r" + str(t-params.currentLeadTime+1))

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
            elif (t-params.currentLeadTime+1) >= 0: # get data from previous iterations
                rhs -= self.repositions[t-params.currentLeadTime+1]

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

    def solve(self, day=0):
        self.currentDay = day
        self.finalDay = self.currentDay + params.horizon

        try:
            # create lp
            self.createLp()

            # write the lp
            self.lp.write(".\\..\\lps\\deterministico_dia" + str(day) + ".lp")

            # solve the model
            self.lp.solve()

            # process solution, get stock reposition for current day
            solution = self.lp.solution
            x = solution.get_values()

            # save the obtained reposition for the current day, if any
            # save the solution data
            for t in range(self.currentDay, self.finalDay):
                # Stock
                s = self.getVariable("s" + str(t))
                if s != 0:
                    val = x[s.col]
                    self.plannedStocks[self.currentDay][t] = val

                # Falta
                fvar = self.getVariable("f" + str(t))
                if fvar != 0:
                    val = x[fvar.col]
                    self.plannedFaults[self.currentDay][t] = val

                # Repositioning
                r = self.getVariable("r" + str(t))
                if r != 0:
                    if t == self.currentDay:
                        self.repositions[self.currentDay] = x[r.col]
                    self.plannedRepositions[self.currentDay][t] = x[r.col]

        except:
            print "Error on t" + str(self.currentDay)
            raise

        return self.problemSolution
