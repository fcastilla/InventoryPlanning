class Parameters:
    initialDay = 0  # initial planning day (t0) (leave at 0 for now, current input contains 61 days)
    horizon = 35  # number of days in planning horizon (maximum 30 days for now, current input contains 61 days)
    initialStockDays = 2  # days of initial stock coverage

    # variable weights
    unitStockageCost = 1  # unit cost of stockage per time unit (same for all days)
    unitPrice = 100  # sell price per product unit (same for all days)
    productAbscenceCost = 300 # cost (per unit) of being short in stock and thus failing to attend a demand
    unitCost = 40  # production cost per product unit (same for al days)

    # other stuff
    repositionInterval = 1
    robustInterval = 7
    currentUncertainty = 0.05
    currentRobustness = 0

    # Scenario data
    uncertainties = [0.2]
    robustness = [1]



