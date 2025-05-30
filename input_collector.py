def collect_user_inputs():
    print("Welcome to the IB Auto-Trading Assistant\n")

    capital = float(input("Enter the amount of capital to allocate for this trade (USD): "))
    symbol = input("Enter the asset symbol (e.g., AAPL, SPY): ").upper()
    timeframe = input("Enter the candle time frame (e.g., 2 mins, 5 mins): ").lower()
    option_type = input("Do you want to trade Calls or Puts? (call/put): ").lower()
    entry_level = float(input("Enter the price level that must be closed above/below to enter the trade: "))
    take_profit = float(input("Enter the take profit level (spot price): "))
    stop_loss = float(input("Enter the stop loss level (spot price): "))

    return {
        "capital": capital,
        "symbol": symbol,
        "timeframe": timeframe,
        "option_type": option_type,
        "entry_level": entry_level,
        "take_profit": take_profit,
        "stop_loss": stop_loss
    }
