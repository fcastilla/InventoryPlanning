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
        self.lp = 0
        self.variables = {}
        self.numCols = 0
        self.problemSolution = 0

    def createScenarios(self):
        self.scenarios = []
        cont = 0
        for s in range(params.numScenarios):
            self.scenarios.append(Scenario(self.pData, self.currentDay, cont))
            cont += 1

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
        numVars += self.createZSVariable()
        numVars += self.createZVariable()

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
        for s in range(len(self.scenarios)):
            scenario = self.scenarios[s]
            for t in range(self.currentDay, self.finalDay+1):
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
        for s in range(len(self.scenarios)):
            scenario = self.scenarios[s]
            for t in range(self.currentDay, self.finalDay+1):
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

    def createZSVariable(self):
        numVars = 0
        # the z variable is for each scenario
        for s in range(len(self.scenarios)):
            scenario = self.scenarios[s]

            # create the variable
            v = Variable()
            v.type = Variable.v_zs
            v.name = "zs_" + scenario.id
            v.col = self.numCols
            v.scenario = scenario.id
            self.variables[v.name] = v
            self.lp.variables.add(names=[v.name])
            self.numCols += 1
            numVars += 1

        return numVars

    def createZVariable(self):
        numVars = 0

        # there is only one z variable in the model
        # create the variable
        v = Variable()
        v.type = Variable.v_z
        v.name = "z"
        v.col = self.numCols
        self.variables[v.name] = v
        self.lp.variables.add(obj=[1.0], names=[v.name])
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
            if t-2 > 0:
                self.initialStock[t] += self.repositions[t-2]

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
            for t in range(self.currentDay, self.finalDay):
                # get the associated demand
                rhs = scenario.forecast[t]

                mind = []
                mval = []

                s = self.getVariable("s_" + scenario.id + "_" + str(t))
                s1 = self.getVariable("s_" + scenario.id + "_" + str(t+1))
                f = self.getVariable("f_" + scenario.id + "_" + str(t))
                r = self.getVariable("r_" + str(t-1))

                mind.append(s.col)
                mval.append(1.0)
                mind.append(f.col)
                mval.append(1.0)
                mind.append(s1.col)
                mval.append(-1.0)

                if r != 0:
                    mind.append(r.col)
                    mval.append(1.0)
                elif (t-1) >= 0:
                    rhs -= self.repositions[t-1]

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

            # get the zs variable
            zs = self.getVariable("zs_" + scenario.id)
            mind.append(zs.col)
            mval.append(1.0)

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

                rhs += scenario.forecast[t]

            # create the constraint
            self.createConstraint(mind,mval,"L",rhs,"foValue_" + scenario.id)
            numCons += 1

        return numCons

    def createRobustConstraint(self):
        numCons = 0

        z = self.getVariable("z")

        # this constraint is for each scenario
        for scenario in self.scenarios:
            mind = []
            mval = []

            mind.append(z.col)
            mval.append(1.0)

            # get the zs variable
            zs = self.getVariable("zs_" + scenario.id)
            mind.append(zs.name)
            mval.append(-1.0)

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

            # save the obtained reposition for the current day, if any
            v = self.getVariable("r_" + str(self.currentDay))
            if v != 0:
                self.repositions[self.currentDay] = x[v.col]

            # save a problem solution with the above data
            self.problemSolution = ProblemSolution(self.currentDay,
                                                   self.repositions[self.currentDay])

        except:
            print "Error on t" + str(self.currentDay)
            raise

        return self.problemSolution
