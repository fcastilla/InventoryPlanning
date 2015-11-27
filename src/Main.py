from src.solvers.DeterministicSolver import DeterministicSolver
from src.solvers.RobustSolver import RobustSolver
from src.graphics.GraphPlotter import GraphPlotter as gp


rSolver = RobustSolver()
rSolver.test()

# dSolver = DeterministicSolver()
# dSolver.solve()
#
# plotter = gp(dSolver.pData, dSolver.solutions)
# plotter.plot()