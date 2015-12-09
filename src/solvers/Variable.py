class Variable:

    v_demand = 1
    v_fault = 2
    v_reposition = 3
    v_stock = 4
    v_yminus = 5
    v_yplus = 6
    v_zsp = 7
    v_zsn = 8
    v_zp = 9
    v_zn = 10
    v_error = 11

    def __init__(self):
        self.name = ""
        self.col = 0
        self.solutionVal = 0
        self.instant = 0
        self.scenario = 0
        self.type = Variable.v_error