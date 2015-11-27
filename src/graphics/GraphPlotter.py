import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np

from src.inputdata.Parameters import Parameters as params


class GraphPlotter:
    def __init__(self, problem_data, problem_solutions):
        self.problem_data = problem_data
        self.problem_solutions = problem_solutions

    def plot(self):
        demandDataList = self.problem_data.demandDataList
        initialDay = params.initialDay
        horizon = params.horizon
        solutions = self.problem_solutions

        #create a new figure
        fig, ax = plt.subplots()
        ax.set_xlabel = "t"
        ax.set_ylabel = "qty"

        #create x coordinates
        x = [i for i in range(params.horizon)]

        #create y coordinates for real demand
        y = [d.demand for d in demandDataList[initialDay:initialDay + horizon]]
        ax.plot(x,y)

        #create dynamic line for demand forecast
        lineDF, = ax.plot(x, np.ma.array([d.forecastDemand
                                         for d in solutions[0].demandData[initialDay:initialDay + horizon]]))

        #create dynamic line for stock
        ydata = [solutions[0].stocks[t] + solutions[0].repositions[t-1] for t in range(initialDay, initialDay+horizon)]
        lineST, = ax.plot(x, np.ma.array(ydata))

        #create dynamic line for time
        lineT, = ax.plot(np.ma.array([0 for i in range(horizon)]),np.linspace(0,20000,horizon))

        def animate(i):
            ydata = [solutions[i].stocks[t] + solutions[i].repositions[t-1] for t in range(initialDay, initialDay+horizon)]
            lineST.set_ydata(np.ma.array(ydata))

            lineDF.set_ydata(np.ma.array([d.forecastDemand
                                         for d in solutions[i].demandData[initialDay:initialDay + horizon]]))

            lineT.set_data(np.ma.array([i for k in range(horizon)]),np.linspace(0,40000,horizon))

            return lineDF, lineST, lineT

        ani = animation.FuncAnimation(fig, animate, np.arange(initialDay, initialDay + horizon), interval=1000, blit=True)

        plt.show()