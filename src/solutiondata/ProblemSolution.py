import copy

# Solution for a given day
class ProblemSolution:
    def __init__(self, day, reposition):
        self.day = day
        self.reposition = reposition

    def __repr__(self):
        return "Day=" + str(self.day) + " - Reposition=" + str(self.reposition)
