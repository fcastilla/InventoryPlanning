class Variable:

    v_demand = 1
    v_fault = 2
    v_reposition = 3
    v_stock = 4
    v_yminus = 5
    v_yplus = 6
    v_error = 7

    def __init__(self):
        self.name = ""
        self.col = 0
        self.solutionVal = 0
        self.instant = 0
        self.period = 0
        self.type = Variable.v_error