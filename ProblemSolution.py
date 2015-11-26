import copy


class ProblemSolution:
    def __init__(self, demandData, repositions, stocks):
        self.demandData = copy.deepcopy(demandData)
        self.repositions = copy.deepcopy(repositions)
        self.stocks = copy.deepcopy(stocks)

    def __repr__(self):
        return repr((self.demandData, self.repositions, self.stocks))
