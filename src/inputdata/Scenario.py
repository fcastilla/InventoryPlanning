from Parameters import Parameters as params
import numpy as np
import math


class Scenario:
    def __init__(self, data, day, id):
        self.currentDay = day
        self.id = str(id)
        self.pData = data
        self.y = [0 for i in range(len(data.demandDataList))]
        self.forecast = [0 for i in range(len(data.demandDataList))]
        self.maxForecast = 0
        self.generate()

    def computeY(self):
        # For each day of each period, calculate y
        # The sum of all y for a given period must be equal to the robustness parameter
        totalPeriods = int(math.ceil(float(params.horizon) / params.robustInterval))

        for p in range(totalPeriods):
            sum = 0
            for d in range(0, params.robustInterval):
                day = (params.robustInterval * p) + d + self.currentDay
                currentY = np.random.uniform(-1,1)
                self.y[day] = currentY
                sum += math.fabs(currentY)

            for d in range(0, params.robustInterval):
                day = (params.robustInterval * p) + d + self.currentDay
                self.y[day] *= (params.currentRobustness / sum)

    def computeForecast(self):
        t0 = self.currentDay
        initialDemandData = self.pData.demandDataList[t0]
        for t in range(t0, t0 + params.horizon):
            demandData = self.pData.demandDataList[t]
            uncertainty = float(params.currentUncertainty * math.sqrt(t-t0))

            # maximum deviation
            deviation = max(0, demandData.demand * uncertainty)

            # additional error
            error = 0
            #error = np.random.normal(0, initialDemandData.demand / 10)

            # forecast for t on this scenario
            self.forecast[t] = max(0, demandData.demand + (deviation * self.y[t]) + error)
            self.maxForecast = max(self.maxForecast, self.forecast[t])


    def generate(self):
        # compute a y array for the associated day for the current scenario
        self.computeY()

        # using the computer y array calculate the demand forecast
        self.computeForecast()