class Parameters:
    initialDay = 0  # initial planning day (t0) (leave at 0 for now, current input contains 61 days)
    horizon = 35  # number of days in planning horizon (maximum 30 days for now, current input contains 61 days)
    initialStockDays = 8  # days of initial stock coverage

    # variable weights
    unitStockageCost = 1  # unit cost of stockage per time unit (same for all days)
    unitPrice = 100  # sell price per product unit (same for all days)
    productAbscenceCost = 3000 # cost (per unit) of being short in stock and thus failing to attend a demand
    unitCost = 40  # production cost per product unit (same for al days)

    # other stuff
    numScenarios = 100 # number of different demand scenarios to be considered on each robust optimization day
    repositionInterval = 3
    leadTime = 5
    robustInterval = 7
    currentLeadTime = 5
    currentRepositionInterval = 3
    currentUncertainty = 0.8
    currentRobustness = 1

    # Experiments data
    uncertainties = [0.3,0.4,0.5]
    robustness = [1,2,3]
    leadTimes = [3,4,5]
    repositionIntervals = [3,5]



