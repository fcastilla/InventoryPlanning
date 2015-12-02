import math
import numpy as np

class DemandData:
    def __init__(self, date, demand):
        self.date = date
        self.demand = demand

    def __repr__(self):
        return str(self.date) + "/" +  str(self.demand) + "/"
