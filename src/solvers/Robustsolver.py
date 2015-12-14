import cplex
import numpy as np
from Variable import Variable
from src.inputdata.Parameters import Parameters as params
from src.inputdata.Scenario import Scenario
from src.inputdata.ProblemData import ProblemData as pdata
from src.solutiondata.ProblemSolution import ProblemSolution


# IN THIS EXAMPLE WE ARE WORKING WITH JUST ONE STORE AND ONE PRODUCT
# 1 time instant = 1 day
# ToDo: parametrize time period discretization

class RobustSolver:
    def __init__(self, pData):
        self.pData = pData
        self.scenarios = []
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

    def createScenarios(self):
        self.scenarios = []
        for s in range(params.numScenarios):
            self.scenarios.append(Scenario(self.pData, self.currentDay, s))

    # Creates the linear program
    def createModel(self):
        self.lp.objective.set_sense(self.lp.objective.sense.maximize)
        self.createVariables()
        self.createConstraints()

    #region Variable Creation
    def createVariables(self):
        numVars = 0
        numVars += self.createRepositionVariable()
        numVars += self.createFVariable()
        numVars += self.createStockVariable()
        numVars += self.createZSVariables()
        numVars += self.createZVariables()

    def createRepositionVariable(self):
        numVars = 0
        repositionDays = [rDay for rDay in self.pData.repositionDays if rDay >= self.currentDay and rDay < self.finalDay]

        # get the maximum forecast for using it as upper bound for r variable
        maxDemand = max(s.maxForecast for s in self.scenarios)

        # The reposition variable remains only for each t in the current planning horizon
        for i in repositionDays:
            v = Variable()
            v.type = Variable.v_reposition
            v.name = "r_" + str(i)
            v.col = self.numCols
            v.instant = i
            self.variables[v.name] = v
            self.lp.variables.add(names=[v.name])
            self.numCols += 1
            numVars += 1

        return numVars

    def createFVariable(self):
        numVars = 0

        # the f variables are for each scenario and for each t of current horizon
        for scenario in self.scenarios:
            for t in range(self.currentDay, self.finalDay):
                # create the variable
                v = Variable()
                v.type = Variable.v_fault
                v.name = "f_" + scenario.id + "_" + str(t)
                v.col = self.numCols
                v.instant = t
                v.scenario = scenario.id
                self.variables[v.name] = v
                self.lp.variables.add(names=[v.name])
                self.numCols += 1
                numVars += 1

        return numVars

    def createStockVariable(self):
        numVars = 0

        # the s variables are for each scenario and for each t of current horizon
        for scenario in self.scenarios:
            for t in range(self.currentDay, self.finalDay):
                # create the variable
                v = Variable()
                v.type = Variable.v_stock
                v.name = "s_" + scenario.id + "_" + str(t)
                v.col = self.numCols
                v.instant = t
                v.scenario = scenario.id
                self.variables[v.name] = v
                self.lp.variables.add(names=[v.name])
                self.numCols += 1
                numVars += 1

        return numVars

    def createZSVariables(self):
        numVars = 0
        # the z variable is for each scenario
        for scenario in self.scenarios:

            # create zsp variable
            v1 = Variable()
            v1.type = Variable.v_zsp
            v1.name = "zsp_" + scenario.id
            v1.col = self.numCols
            v1.scenario = scenario.id
            self.variables[v1.name] = v1
            self.lp.variables.add(names=[v1.name])
            self.numCols += 1
            numVars += 1

            #create zsn variable
            v2 = Variable()
            v2.type = Variable.v_zsn
            v2.name = "zsn_" + scenario.id
            v2.col = self.numCols
            v2.scenario = scenario.id
            self.variables[v2.name] = v2
            self.lp.variables.add(names=[v2.name])
            self.numCols += 1
            numVars += 1

        return numVars

    def createZVariables(self):
        numVars = 0

        # create the zp variable
        v1 = Variable()
        v1.type = Variable.v_zp
        v1.name = "zp"
        v1.col = self.numCols
        self.variables[v1.name] = v1
        self.lp.variables.add(obj=[1.0], names=[v1.name])
        self.numCols += 1
        numVars += 1

        # create the zn variable
        v2 = Variable()
        v2.type = Variable.v_zn
        v2.name = "zn"
        v2.col = self.numCols
        self.variables[v2.name] = v2
        self.lp.variables.add(obj=[-1.0], names=[v2.name])
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
        numConst = 0
        numConst += self.createInitialStockConstraint()
        numConst += self.createStockFlowConstraint()
        numConst += self.createFOScenarioConstraint()
        numConst += self.createRobustConstraint()

    def computeInitialStock(self):
        t = self.currentDay
        if t == params.initialDay:
            self.initialStock[t] = self.pData.getInitialStock()
        else:
            self.initialStock[t] = self.initialStock[t-1] - self.pData.demandDataList[t-1].demand
            if t - params.currentLeadTime > 0:
                self.initialStock[t] += self.repositions[t-params.currentLeadTime]

        self.initialStock[t] = max(0, self.initialStock[t])

    def createInitialStockConstraint(self):
        numCons = 0

        # get the initial stock value for the current day, which will be the same for all scenarios.
        self.computeInitialStock()

        # this constraint is current day, for each scenario
        for scenario in self.scenarios:
            # get the initial stock variable for current day and scenario
            v = self.variables["s_" + scenario.id + "_"  + str(self.currentDay)]
            mind = [v.col]
            mval = [1.0]
            self.createConstraint(mind,mval,"E",self.initialStock[self.currentDay],"initial_stock_" + scenario.id)
            numCons += 1

        return numCons

    def createStockFlowConstraint(self):
        numCons = 0
        # s_{s,t} + r_{t-1} + f_{s,t} - s_{s,t+1} = d_{s,t}

        # this constraint is for each scenatio and each t in the horizon
        for scenario in self.scenarios:
            for t in range(self.currentDay, self.finalDay-1):
                # get the associated demand
                rhs = scenario.forecast[t]

                mind = []
                mval = []

                s = self.getVariable("s_" + scenario.id + "_" + str(t))
                s1 = self.getVariable("s_" + scenario.id + "_" + str(t+1))
                f = self.getVariable("f_" + scenario.id + "_" + str(t))
                r = self.getVariable("r_" + str(t-params.currentLeadTime+1))

                mind.append(s.col)
                mval.append(1.0)
                mind.append(f.col)
                mval.append(1.0)

                if s1 != 0:
                    mind.append(s1.col)
                    mval.append(-1.0)

                if r != 0:
                    mind.append(r.col)
                    mval.append(1.0)
                elif (t-params.currentLeadTime+1) >= 0:
                    rhs -= self.repositions[t-params.currentLeadTime+1]

                self.createConstraint(mind,mval,"E",rhs,"stock_flow_" + scenario.id + "_" + str(t))
                numCons += 1

        return numCons

    def createFOScenarioConstraint(self):
        numCons = 0

        # this constraint is for each scenario
        for scenario in self.scenarios:
            mind = []
            mval = []
            rhs = 0

            # get the zsp variable
            zsp = self.getVariable("zsp_" + scenario.id)
            mind.append(zsp.col)
            mval.append(1.0)

            # get the zpn variable
            zsn = self.getVariable("zsn_" + scenario.id)
            mind.append(zsn.col)
            mval.append(-1.0)

            # get other variables, for each t
            for t in range(self.currentDay, self.finalDay):
                s = self.getVariable("s_" + scenario.id + "_" + str(t))
                r = self.getVariable("r_" + str(t))
                f = self.getVariable("f_" + scenario.id + "_" + str(t))

                mind.append(s.col)
                mval.append(params.unitStockageCost)

                if r != 0:
                    mind.append(r.col)
                    mval.append(params.unitCost)

                mind.append(f.col)
                mval.append(params.productAbscenceCost)

                rhs += (params.unitPrice * scenario.forecast[t])

            # create the constraint
            self.createConstraint(mind,mval,"E",rhs,"foValue_" + scenario.id)
            numCons += 1

        return numCons

    def createRobustConstraint(self):
        numCons = 0

        zp = self.getVariable("zp")
        zn = self.getVariable("zn")

        # this constraint is for each scenario
        for scenario in self.scenarios:
            mind = []
            mval = []

            mind.append(zp.col)
            mval.append(1.0)

            mind.append(zn.col)
            mval.append(-1.0)

            # get the zsp variable
            zsp = self.getVariable("zsp_" + scenario.id)
            mind.append(zsp.col)
            mval.append(-1.0)

            # get the zsn variable
            zsn = self.getVariable("zsn_" + scenario.id)
            mind.append(zsn.col)
            mval.append(1.0)

            self.createConstraint(mind,mval,"L",0.0,"robust_" + scenario.id)
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

    def solve(self, day):
        self.currentDay = day
        self.finalDay = self.currentDay + params.horizon

        # create the list of scenarios for the current day
        self.createScenarios()

        try:
            # create the lp model
            self.createLp()

            # write the lp
            self.lp.write(".\\..\\lps\\robusto_dia" + str(day) + ".lp")

            # solve the model
            self.lp.solve()

            # process problem solution
            solution = self.lp.solution
            x = solution.get_values()

            # determinar qual foi o cenario restritivo
            zp = self.getVariable("zp")
            zn = self.getVariable("zn")

            zpVal = x[zp.col]
            znVal = x[zn.col]

            if zpVal > 0:
                vname = "zsp"
                zval = zpVal
            else:
                vname = "zsn"
                zval = znVal

            mScenario = 0
            for scenario in self.scenarios:
                zvar = self.getVariable(vname + "_" + str(scenario.id))
                if x[zvar.col] == zval:
                    mScenario = scenario
                    break

            # save the solution data
            for t in range(self.currentDay, self.finalDay):
                # Stock
                s = self.getVariable("s_" + str(mScenario.id) + "_" + str(t))
                if s != 0:
                    val = x[s.col]
                    self.plannedStocks[self.currentDay][t] = val

                # Falta
                fvar = self.getVariable("f_" + str(mScenario.id) + "_" + str(t))
                if fvar != 0:
                    val = x[fvar.col]
                    self.plannedFaults[self.currentDay][t] = val

                # Repositioning
                r = self.getVariable("r_" + str(t))
                if r != 0:
                    if t == self.currentDay:
                        self.repositions[self.currentDay] = x[r.col]
                    self.plannedRepositions[self.currentDay][t] = x[r.col]

        except:
            print "Error on t" + str(self.currentDay)
            raise

        return self.problemSolution
