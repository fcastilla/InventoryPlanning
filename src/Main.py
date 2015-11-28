from src.solvers.DeterministicSolver import DeterministicSolver
from src.solvers.RobustSolver import RobustSolver
from src.graphics.GraphPlotter import GraphPlotter as gp

# dSolver = DeterministicSolver()
# dSolver.solve()

rSolver = RobustSolver()
rSolver.solve()

plotter = gp(rSolver.pData, rSolver.solutions)
plotter.plotObjVal()

# plotter = gp(dSolver.pData, dSolver.solutions)
# plotter.plot()