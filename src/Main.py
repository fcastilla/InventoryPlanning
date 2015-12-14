from datetime import datetime

import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.animation as animation
from matplotlib.font_manager import FontProperties

from src.inputdata.Parameters import Parameters as params
from src.inputdata.ProblemData import ProblemData
from src.solvers.DeterministicSolver import DeterministicSolver
from src.solvers.RobustSolver import RobustSolver
from src.solutiondata.SimulationData import SimulationData


class InventoryPlanner:
    def __init__(self):
        self.data = ProblemData()
        self.totalDays = len(self.data.demandDataList)
        self.initialDay = params.initialDay
        self.finalDay = self.initialDay + params.horizon
        self.date = datetime.now()
        self.dSolver = DeterministicSolver(self.data)
        self.rSolver = RobustSolver(self.data)
        self.dSimulationData = SimulationData()
        self.rSimulationData = SimulationData()
        matplotlib.rcParams.update({'font.size': 10})

        np.random.seed(0)

    def runBatchExperiments(self):
        print "Starting inventory planning..."

        # Call both solvers, deterministic and robust for each planning day
        for u in params.uncertainties:
            params.currentUncertainty = u
            for r in params.robustness:
                params.currentRobustness = r
                for ri in params.repositionIntervals:
                    params.currentRepositionInterval = ri
                    for lt in params.leadTimes:
                        params.currentLeadTime = lt
                        self.executePlanning()

    def executePlanning(self):
        # initialize problem data
        self.data.setRepositionDays()

        # create solvers
        self.dSolver = DeterministicSolver(self.data)
        self.rSolver = RobustSolver(self.data)

        for t in range(self.initialDay, self.finalDay):
            # compute forecast for current day
            self.data.computeForecast(t)

            print "Running deterministic solver for day " + str(t)
            self.dSolver.solve(t)

            print "Running robust solver for day " + str(t)
            self.rSolver.solve(t)

        self.computeSimulationData()
        self.saveAndPlotResult()
        self.doSimulation()

    def computeSimulationData(self):
        # Use obtained repositions to calculate stocks and faults at each day
        dFault = [0 for i in range(self.totalDays)]
        rFault = [0 for i in range(self.totalDays)]

        dStock = [0 for i in range(self.totalDays)]
        rStock = [0 for i in range(self.totalDays)]

        dStock[params.initialDay] = self.data.getInitialStock()
        rStock[params.initialDay] = self.data.getInitialStock()

        for t in range(self.initialDay, self.finalDay - 1):
            dStock[t+1] = dStock[t] - self.data.demandDataList[t].demand
            rStock[t+1] = rStock[t] - self.data.demandDataList[t].demand

            if t-1 > 0:
                dStock[t+1] += self.dSolver.repositions[t-1]
                rStock[t+1] += self.rSolver.repositions[t-1]

            if dStock[t+1] < 0:
                dFault[t+1] = dStock[t+1]
                dStock[t+1] = 0

            if rStock[t+1] < 0:
                rFault[t+1] = rStock[t+1]
                rStock[t+1] = 0

        # compute objective values for each solver
        dObj = [0 for i in range(self.totalDays)]
        rObj = [0 for i in range(self.totalDays)]

        for t in range(self.initialDay, self.finalDay):
            demand = self.data.demandDataList[t].demand
            dVal = (params.unitPrice*demand) - (params.productAbscenceCost*dFault[t]) - \
                   (params.unitCost*self.dSolver.repositions[t]) - (params.unitStockageCost*dStock[t])
            rVal = (params.unitPrice*demand) - (params.productAbscenceCost*rFault[t]) - \
                   (params.unitCost*self.rSolver.repositions[t]) - (params.unitStockageCost*rStock[t])

            if t == self.initialDay:
                dObj[t] = dVal
                rObj[t] = rVal
            else:
                dObj[t] = dObj[t-1] + dVal
                rObj[t] = rObj[t-1] + rVal

        self.dSimulationData = SimulationData(dObj,dFault,dStock,self.dSolver.repositions)
        self.rSimulationData = SimulationData(rObj,rFault,rStock,self.rSolver.repositions)

    def saveAndPlotResult(self):
        fig = plt.figure()
        fontP = FontProperties()
        fontP.set_size('small')
        for day in range(params.initialDay, params.initialDay + params.horizon):
            fig.clf()
            fig.suptitle('Results for Day ' + str(day) + " | Error: " + str(params.currentUncertainty) +
                         " | Robustness: " + str(params.currentRobustness) + " | RepInterval: " +
                         str(params.currentRepositionInterval) + " | LeadTime: " + str(params.currentLeadTime), size=13)
            gs = gridspec.GridSpec(3, 3, hspace=0.9, wspace=0.5)

            # Demand data result
            ax1 = fig.add_subplot(gs[0, : ])

            days = np.arange(day, day + params.horizon)
            demand = [0 for i in range(params.horizon)]
            forecast = [0 for i in range(params.horizon)]
            error = [0 for i in range(params.horizon)]
            cont = 0

            for t in range(day, day + params.horizon):
                demand[cont] = self.data.demandDataList[t].demand
                forecast[cont] = self.data.getForecast(day,t)
                error[cont] = forecast[cont] * (self.data.getCurrentUncertaintyInterval(day, t)/5)
                cont += 1

            ax1.errorbar(days, forecast, yerr=error, fmt='o')

            ax1.plot(days, forecast, label="Forecast Demand")
            ax1.plot(days, demand, label="Real Demand")
            ax1.set_xlim(day, day+params.horizon)
            ax1.set_ylim(0,max(error) + max(forecast) + 2000)
            ax1.legend(loc='upper center', bbox_to_anchor=(0.5, 1.3), ncol=2, fancybox=True, shadow=True)

            # Robust stock
            ax2 = fig.add_subplot(gs[1, 0])
            ax2.set_title("Stock", size=12)
            ax2.set_ylim(0,max(self.rSolver.plannedStocks[day]) + 10000)

            ax2.bar(days, self.rSolver.plannedStocks[day][day:day+params.horizon], color="b")

            # Robust reposition
            ax3 = fig.add_subplot(gs[1, 1])
            ax3.set_title("Reposition", size=12)

            ylim3 = max(self.rSolver.plannedRepositions[day]) + 10000
            ax3.set_ylim(0, ylim3)

            ax3.text((len(days) / 2.) + min(days), ylim3 * 1.45, 'Robust Model', size=13,
                horizontalalignment='center',
                verticalalignment='top',
                multialignment='center')

            ax3.bar(days, self.rSolver.plannedRepositions[day][day:day+params.horizon], color="g")

            # Robust fault
            ax4 = fig.add_subplot(gs[1, 2])
            ax4.set_title("Lack", size=12)
            ax4.set_ylim(0,max(self.rSolver.plannedFaults[day]) + 10000)

            ax4.bar(days, self.rSolver.plannedFaults[day][day:day+params.horizon], color="r")

            # Deterministic stock
            ax5 = fig.add_subplot(gs[2, 0])
            ax5.set_title("Stock", size=12)
            ax5.set_ylim(0,max(self.dSolver.plannedStocks[day]) + 10000)

            ax5.bar(days, self.dSolver.plannedStocks[day][day:day+params.horizon], color="b")

            # Robust reposition
            ax6 = fig.add_subplot(gs[2, 1])
            ax6.set_title("Reposition", size=12)

            ylim6 = max(self.dSolver.plannedRepositions[day]) + 10000
            ax6.set_ylim(0, ylim6)

            ax6.text((len(days) / 2.) + min(days), ylim6 * 1.45, 'Deterministic Model', size=13,
                horizontalalignment='center',
                verticalalignment='top',
                multialignment='center')

            ax6.bar(days, self.dSolver.plannedRepositions[day][day:day+params.horizon], color="g")

            # Robust fault
            ax7 = fig.add_subplot(gs[2, 2])
            ax7.set_title("Lack", size=12)
            ax7.set_ylim(0,max(self.dSolver.plannedFaults[day]) + 10000)

            ax7.bar(days, self.dSolver.plannedFaults[day][day:day+params.horizon], color="r")

            path = "../output/Error" + str(params.currentUncertainty) + "_Robustness" + str(params.currentRobustness) + \
                   "_RepositionInterval" + str(params.currentRepositionInterval) + "_LeadTime" + str(params.currentLeadTime) + "/DailyGraphs/"
            filename = path + "dummy.txt"
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))

            fig.savefig(path + "Graph_Day" + str(day) + ".png",dpi=150,facecolor='white')

            # save file
            path = "../output/Error" + str(params.currentUncertainty) + "_Robustness" + str(params.currentRobustness) + \
                   "_RepositionInterval" + str(params.currentRepositionInterval) + "_LeadTime" + str(params.currentLeadTime) + "/Results/"
            filename = path + "Result_Day" + str(day) + ".csv"
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))

            f = open(filename,"w")
            line = "Day; Uncertainty; Robustness; Reposition Interval; Lead Time; Real Demand; Forecast; Error; Robust Stock;" \
                   "Robust Reposition; Robust Lack; Deterministic Stock; Deterministic Reposition; Deterministic Lack\n"
            f.write(line)
            cont = 0
            for t in range(day, day + params.horizon):
                line = str(t) + ";"
                line += str(params.currentUncertainty).replace(".",",") + ";"
                line += str(params.currentRobustness).replace(".",",") + ";"
                line += str(params.currentRepositionInterval).replace(".",",") + ";"
                line += str(params.currentLeadTime).replace(".",",") + ";"
                line += '{:.2f}'.format(demand[cont]).replace(".",",") + ";"
                line += '{:.2f}'.format(forecast[cont]).replace(".",",") + ";"
                line += '{:.2f}'.format(error[cont]).replace(".",",") + ";"
                line += '{:.2f}'.format(self.rSolver.plannedStocks[day][t]).replace(".",",") + ";"
                line += '{:.2f}'.format(self.rSolver.plannedRepositions[day][t]).replace(".",",") + ";"
                line += '{:.2f}'.format(self.rSolver.plannedFaults[day][t]).replace(".",",") + ";"
                line += '{:.2f}'.format(self.dSolver.plannedStocks[day][t]).replace(".",",") + ";"
                line += '{:.2f}'.format(self.dSolver.plannedRepositions[day][t]).replace(".",",") + ";"
                line += '{:.2f}'.format(self.dSolver.plannedFaults[day][t]).replace(".",",") + ";"
                line += "\n"
                cont += 1
                f.write(line)
            f.close()

    def doSimulation(self):
        print(animation.writers.list())
        Writer = animation.writers['ffmpeg']
        writer = Writer(fps=1, metadata=dict(artist='Fabian'), bitrate=1800)

        fontP = FontProperties()
        fontP.set_size('small')

        fig = plt.figure()
        fig.suptitle("Simulation | Error: " + str(params.currentUncertainty) +
                         " | Robustness: " + str(params.currentRobustness) + " | RepInterval: " +
                         str(params.currentRepositionInterval) + " | LeadTime: " + str(params.currentLeadTime), size=13)
        gs = gridspec.GridSpec(2, 1, hspace=0.3, wspace=0.5)

        # Obj Functions
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.set_ylim(0, max(max(self.dSimulationData.obj), max(self.rSimulationData.obj)) + 100000)
        ax1.set_xlim(params.initialDay, params.initialDay + params.horizon)
        roLine, = ax1.plot([],[],"r", label="Robust Obj")
        doLine, = ax1.plot([],[],"b", label="Deterministic Obj")
        ax1.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=2, fancybox=True, shadow=True, prop=fontP)

        # Stocks
        ax2 = fig.add_subplot(gs[1, 0])
        ax2.set_title("Stocks")
        ax2.set_ylim(0, max(max(self.dSimulationData.stock), max(self.rSimulationData.stock)) + 10000)
        ax2.set_xlim(params.initialDay, params.initialDay + params.horizon)
        rsLine, = ax2.plot([],[],"r", label="Robust Stock")
        dsLine, = ax2.plot([],[],"b", label="Deterministic Stock")
        ax2.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=2, fancybox=True, shadow=True, prop=fontP)

        lineAnimation = animation.FuncAnimation(fig, self.updateFrame, frames=params.horizon+1,
                                                fargs=(roLine, doLine, rsLine, dsLine),
                                                interval=1000, blit=True)

        path = "../output/Error" + str(params.currentUncertainty) + "_Robustness" + str(params.currentRobustness) + \
               "_RepositionInterval" + str(params.currentRepositionInterval) + "_LeadTime" + str(params.currentLeadTime) + "/Simulation/"
        filename = path + "dummy.txt"
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))

        # save animation
        lineAnimation.save(path + 'simulation.mp4', writer=writer, savefig_kwargs={'facecolor':'white'})

        # save file
        filename = path + "simulation.csv"
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))

        f = open(filename,"w")
        line = "Day; Uncertainty; Robustness; Reposition Interval; Lead Time; Real Demand;" \
               "Robust Objective; Robust Stock; Robust Reposition; Robust Fault; " \
               "Deterministic Objective; Deterministic Stock; Deterministic Reposition; Deterministic Fault \n"
        f.write(line)

        for t in range(self.initialDay, self.initialDay + params.horizon):
            line = str(t) + ";"
            line += str(params.currentUncertainty).replace(".",",") + ";"
            line += str(params.currentRobustness).replace(".",",") + ";"
            line += str(params.currentRepositionInterval).replace(".",",") + ";"
            line += str(params.currentLeadTime).replace(".",",") + ";"
            line += '{:.2f}'.format(self.data.demandDataList[t].demand).replace(".",",") + ";"
            line += '{:.2f}'.format(self.rSimulationData.obj[t]).replace(".",",") + ";"
            line += '{:.2f}'.format(self.rSimulationData.stock[t]).replace(".",",") + ";"
            line += '{:.2f}'.format(self.rSimulationData.reposition[t]).replace(".",",") + ";"
            line += '{:.2f}'.format(self.rSimulationData.fault[t]).replace(".",",") + ";"
            line += '{:.2f}'.format(self.dSimulationData.obj[t]).replace(".",",") + ";"
            line += '{:.2f}'.format(self.dSimulationData.stock[t]).replace(".",",") + ";"
            line += '{:.2f}'.format(self.dSimulationData.reposition[t]).replace(".",",") + ";"
            line += '{:.2f}'.format(self.dSimulationData.fault[t]).replace(".",",") + ";"
            line += "\n"
            f.write(line)
        f.close()

    def updateFrame(self, i, roLine, doLine, rsLine, dsLine, rRline=0):
        days = [d for d in range(self.initialDay, self.initialDay + i + 1)]
        robj = self.rSimulationData.obj[self.initialDay:self.initialDay+i+1]
        dobj = self.dSimulationData.obj[self.initialDay:self.initialDay+i+1]
        rstock = self.rSimulationData.stock[self.initialDay:self.initialDay+i+1]
        dstock = self.dSimulationData.stock[self.initialDay:self.initialDay+i+1]
        roLine.set_data(days, robj)
        doLine.set_data(days, dobj)
        rsLine.set_data(days, rstock)
        dsLine.set_data(days, dstock)
        return roLine, doLine, rsLine, dsLine

    def printToFile(self, day, realDemand, dObj, dRep, rObj, rRep):
        fileName = ".\\..\\output\\Inventory_u" + str(params.currentUncertainty).replace(".","") + \
                   "_r" + str(params.currentRobustness).replace(".","") + ".csv"

        line = str(day) + ";" + '{:.2f}'.format(realDemand).replace(".",",") + ";" + '{:.2f}'.format(dObj).replace(".",",") + ";" \
               +  '{:.2f}'.format(dRep).replace(".",",") + ";" + '{:.2f}'.format(rObj).replace(".",",") + ";" \
               + '{:.2f}'.format(rRep).replace(".",",") + "\n"

        f = open(fileName, "a")
        f.write(line)
        f.close()

planner = InventoryPlanner()
planner.runBatchExperiments()

# fileName = ".\\..\\output\\StockNReposition_u" + str(params.currentUncertainty) + "_r" +\
#                        str(params.currentRobustness) + "_day" + str(day) + ".csv"
# f = open(fileName,"a")
# line = "Dia;Scenario;Demand;Stock;Fault;Reposition\n"
# f.write(line)
# for t in range(self.currentDay, self.finalDay):
#     line = str(t) + ";" + str(mScenario.id) + ";"
#
#     # Demand
#     demand = mScenario.forecast[t]
#     line += '{:.2f}'.format(demand).replace(".",",") + ";"
#
#     # Stock
#     s = self.getVariable("s_" + str(mScenario.id) + "_" + str(t))
#     if s != 0:
#         val = x[s.col]
#         line += '{:.2f}'.format(val).replace(".",",") + ";"
#     else:
#         line += "0;"
#
#     # Falta
#     fvar = self.getVariable("f_" + str(mScenario.id) + "_" + str(t))
#     if f != 0:
#         val = x[fvar.col]
#         line += '{:.2f}'.format(val).replace(".",",") + ";"
#     else:
#         line += "0;"
#
#     # Repositioning
#     r = self.getVariable("r_" + str(t))
#     if r != 0:
#         if t == self.currentDay:
#             self.repositions[self.currentDay] = x[r.col]
#         line += '{:.2f}'.format(x[r.col]).replace(".",",") + ";"
#     else:
#         line += "0;"
#
#     line += "\n"
#     f.write(line)
# f.close()