import copy


class ProblemSolution:
    def __init__(self, demandData, repositions, stocks, objVal):
        self.demandData = copy.deepcopy(demandData)
        self.repositions = copy.deepcopy(repositions)
        self.stocks = copy.deepcopy(stocks)
        self.objVal = objVal

    def __repr__(self):
        return "Obj= " + str(self.objVal) + \
               repr(self.demandData) + "/" + repr(self.repositions) + "/" + repr(self.stocks)
