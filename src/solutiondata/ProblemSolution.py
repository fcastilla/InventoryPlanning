import copy

# Solution for a given day
class ProblemSolution:
    def __init__(self, day, reposition, objVal):
        self.day = day
        self.reposition = reposition
        self.objVal = objVal

    def __repr__(self):
        return "Day=" + str(self.day) + " - Reposition=" + str(self.reposition) + \
               " - ObjVal=" + str(self.objVal)
