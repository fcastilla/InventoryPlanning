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
        self.currentPeriod = 0
        self.totalPeriods = int(params.horizon / params.robustInterval)
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
        numVars += self.createTimeIndexedVariable("d", Variable.v_demand, 0.0)
        numVars += self.createTimeIndexedVariable("f", Variable.v_fault, -params.productAbscenceCost)
        numVars += self.createTimeIndexedVariable("r", Variable.v_reposition, -params.unitCost, params.repositionInterval)
        numVars += self.createTimeIndexedVariable("s", Variable.v_stock, -params.unitStockageCost)
        numVars += self.createTimeIndexedVariable("yplus", Variable.v_yplus, 0.0, 1, 0.0, 1.0)
        numVars += self.createTimeIndexedVariable("yminus", Variable.v_yminus, 0.0, 1, 0.0, 1.0)
        # numVars += self.createTimeIndexedVariable("pi", 0.0, params.robustInterval)  # 1 for each 'robust' period
        # numVars += self.createTimeIndexedVariable("gamma")  # 1 for eac time instant

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
        numConst += self.createDemandConstraint()
        numConst += self.createRobustConstraint()

    def createInitialStockConstraint(self):
        v = self.variables["s" + str(self.currentDay)]
        mind = [v.col]
        mval = [1.0]
        self.createConstraint(mind,mval,"E",self.pData.getInitialStock(),"initial_stock")
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

            self.createConstraint(mind,mval,"E",mean,"c_demand" + str(t))

            numCons += 1

        return numCons

    def createRobustConstraint_old(self):
        numCons = 0
        mult = params.robustConstraintMultiplier
        sense = params.robustConstraintSense

        for i in range(self.currentPeriod,self.totalPeriods):
            mind = []
            mval = []
            p = i * params.robustInterval

            pi = self.getVariable("pi" + str(p)) # pi variable
            mind.append(pi.name)
            mval.append(params.pessimism * mult)

            rhs = 0.0

            for t in range(p, p + params.robustInterval):
                demandData = self.pData.demandDataList[t]
                mean = demandData.demand
                rhs += (mean * mult)

                s = self.getVariable("s" + str(t))
                mind.append(s.name)
                mval.append(1.0 * mult)

                s1 = self.getVariable("s" + str(t+1))
                if s1 != 0:
                    mind.append(s1.name)
                    mval.append(-1.0 * mult)

                f = self.getVariable("f" + str(t))
                mind.append(f.name)
                mval.append(1.0 * mult)

                r = self.getVariable("r" + str(t-1))
                if r != 0:
                    mind.append(r.name)
                    mval.append(1.0 * mult)

                gamma = self.getVariable("gamma" + str(t))
                mind.append(gamma.name)
                mval.append(1.0 * mult)

            self.createConstraint(mind,mval,sense,rhs,"c_robust" + str(p))

            numCons += 1

        return numCons

    def createRobustConstraint(self):
        numCons = 0
        for p in range(self.currentPeriod, self.totalPeriods):
            mind = []
            mval = []
            rhs = self.pData.getPessimism(p)

            finalDay = min(((p * params.robustInterval) + params.robustInterval), self.finalDay)

            for t in range(self.currentDay, finalDay):
                yplus = self.getVariable("yplus" + str(t))
                mind.append(yplus.name)
                mval.append(1.0)

                yminus = self.getVariable("yminus" + str(t))
                mind.append(yminus.name)
                mval.append(1.0)

            self.createConstraint(mind,mval,"L",rhs,"c_robust" + str(p))

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
        try:
            while iterations < 1:
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
                self.lp.write(".\\..\\lps\\robust_period_" + str(self.currentPeriod) + ".lp")
                self.lp.solve()

                # process solution, get stock reposition for current day and stock for next planning day
                solution = self.lp.solution
                objValue = solution.get_objective_value()
                x = solution.get_values()

                print "**********************************************"
                print "Robust - Period " + str(self.currentPeriod) + " obj val: " + str(objValue)

                for k,v in self.variables.iteritems():
                    # load the reposition and stock quantity
                    col = v.col
                    t = v.instant
                    solVal = x[col]

                    print v.name, "=", solVal

                    if v.type == Variable.v_reposition:
                        self.repositions[t] = solVal
                    elif v.type == Variable.v_stock:
                        self.initialStock[t] = solVal

                self.solutions.append(ProblemSolution(self.pData.demandDataList,
                                                      self.repositions, self.initialStock,objValue))

                self.currentPeriod += 1
                self.currentDay = self.currentPeriod * params.robustInterval
                self.variables = {}
                self.numCols = 0

                iterations += 1
        except:
            print "Error on t" + str(self.currentDay)
            raise
