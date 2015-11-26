class Parameters:
    initialDay = 0  # initial planning day (t0) (leave at 0 for now, current input contains 61 days)
    horizon = 30  # number of days in planning horizon (maximum 30 days for now, current input contains 61 days)
    initialStockDays = 4  # days of initial stock coverage
    unitStockageCost = 1  # unit cost of stockage per time unit (same for all days)
    unitPrice = 100  # sell price per product unit (same for all days)
    unitCost = 40  # production cost per product unit (same for al days)
