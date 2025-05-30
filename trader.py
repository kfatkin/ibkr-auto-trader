from ib_insync import *
import time
import pandas as pd
import signal
import sys
import matplotlib.pyplot as plt
from logger_setup import setup_logger

ib = None  # Global reference for signal handler
print(f"Running trader.py from: {__file__}")

def run_trader(user_data, client_id):
    global ib
    logger = setup_logger(user_data['symbol'])
    logger.info("Starting trader for %s", user_data['symbol'])

    def signal_handler(sig, frame):
        if ib is not None and ib.isConnected():
            ib.disconnect()
            logger.info("Disconnected from IB via signal (Ctrl+C)")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        logger.info("Connecting to IB...")
        ib = connect_ib(logger, client_id)
        logger.info("Fetching option chain...")
        contracts, tickers = get_otm_options(ib, user_data['symbol'], user_data['option_type'], logger, user_data['capital'])
        logger.info("Option chain fetched. Prompting user for contract selection...")
        selected_contract = select_contract(contracts, tickers, logger)
        if selected_contract is None:
            logger.warning("No contract selected. Exiting.")
            return

        logger.info("Monitoring and trading...")
        monitor_and_trade(ib, user_data, selected_contract, logger)
    except Exception as e:
        logger.exception("An error occurred: %s", e)
    finally:
        if ib is not None and ib.isConnected():
            ib.disconnect()
            logger.info("Disconnected from IB (finally block)")

def connect_ib(logger, client_id):
    ib = IB()
    ib.connect('127.0.0.1', 7496, clientId=client_id)
    logger.info(f"Connected to IB with clientId {client_id}")
    return ib
def get_otm_options(ib, symbol, option_type, logger, capital_limit=1000):
    stock = Stock(symbol, 'SMART', 'USD')
    ib.qualifyContracts(stock)
    logger.info("Stock contract qualified: %s", stock)

    chains = ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
    chain = next(c for c in chains if c.exchange == 'SMART')
    logger.info("Option chain retrieved: %s", chain)

    market_price = ib.reqMktData(stock, '', False, False)
    ib.sleep(2)
    spot_price = float(market_price.last)
    logger.info("Spot price: %.2f", spot_price)

    if option_type == 'call':
        strikes = sorted([strike for strike in chain.strikes if strike > spot_price])
    else:
        strikes = sorted([strike for strike in chain.strikes if strike < spot_price], reverse=True)

    strikes = [strike for strike in strikes if abs(strike - spot_price) / spot_price <= 0.10]
    expiry = sorted(chain.expirations)[0]
    logger.info("Using expiration: %s", expiry)

    contracts = []
    for strike in strikes:
        option = Option(
            symbol=symbol,
            lastTradeDateOrContractMonth=expiry,
            strike=strike,
            right=option_type.upper(),
            exchange='SMART',
            currency='USD',
            tradingClass=chain.tradingClass,
            multiplier=chain.multiplier
        )
        ib.qualifyContracts(option)
        contracts.append(option)
        logger.info("Qualified option contract: %s", option)

    tickers = [ib.reqMktData(contract, '', False, False) for contract in contracts]
    ib.sleep(2)
    logger.info("Market data retrieved for contracts.")
    return contracts, tickers

def select_contract(contracts, tickers, logger):
    print("✅ select_contract() with logger loaded")
    valid_contracts = visualize_contract_scores(contracts, tickers)

    if not valid_contracts:
        print("⚠️ No contracts available for selection.")
        return None

    while True:
        try:
            print("📌 Ready for user input...")
            choice = int(input(f"\nSelect a contract to trade (1-{len(valid_contracts)}): "))
            if 1 <= choice <= len(valid_contracts):
                selected_contract, selected_ticker = valid_contracts[choice - 1]
                print(f"✅ Contract {choice} selected.")
                logger.info(
                    "User selected contract: Strike=%.2f | Δ=%s | Γ=%s | θ=%s | ν=%s | IV=%s | Ask=%s",
                    selected_contract.strike,
                    getattr(selected_ticker.modelGreeks, 'delta', 'N/A'),
                    getattr(selected_ticker.modelGreeks, 'gamma', 'N/A'),
                    getattr(selected_ticker.modelGreeks, 'theta', 'N/A'),
                    getattr(selected_ticker.modelGreeks, 'vega', 'N/A'),
                    getattr(selected_ticker.modelGreeks, 'impliedVolatility', 'N/A'),
                    selected_ticker.ask if selected_ticker.ask is not None else 'N/A'
                )
                return selected_contract
            else:
                print("❌ Invalid choice. Please select a valid number.")
        except ValueError as e:
            print(f"❌ Invalid input: {e}")

def visualize_contract_scores(contracts, tickers):
    import matplotlib.pyplot as plt

    scores = []
    labels = []
    valid_contracts = []

    for contract, ticker in zip(contracts, tickers):
        try:
            ask = ticker.ask
            delta = ticker.modelGreeks.delta
            gamma = ticker.modelGreeks.gamma
            theta = ticker.modelGreeks.theta
            vega = ticker.modelGreeks.vega
            iv = ticker.modelGreeks.impliedVolatility

            if ask == 0 or delta is None:
                continue

            score = (
                - abs(delta - 0.25) * 2.0 +
                gamma * 1.5 -
                abs(theta) * 1.0 -
                iv * 0.5
            )

            scores.append(score)
            labels.append(f"{contract.strike} | Δ: {delta:.2f} | Γ: {gamma:.2f} | θ: {theta:.2f} | ν: {vega:.2f} | IV: {iv:.2f} | Ask: {ask:.2f}")
            valid_contracts.append((contract, ticker))

        except Exception:
            continue

    if scores:
        plt.figure(figsize=(12, 6))
        bars = plt.bar(range(len(scores)), scores, color='blue')
        best_index = scores.index(max(scores))
        bars[best_index].set_color('red')

        plt.xticks(range(len(scores)), labels, rotation=90)
        plt.ylabel("Score")
        plt.title("Option Contract Scores (Best in Red)")
        plt.tight_layout()
        plt.show(block=True)

    if not valid_contracts:
        print("⚠️ No contracts had complete data for visualization. Showing all available contracts.")
        valid_contracts = [(c, t) for c, t in zip(contracts, tickers)]

    valid_contracts.sort(key=lambda x: getattr(x[1].modelGreeks, 'delta', -999), reverse=True)

    print("\nAvailable Contracts:")
    for i, (contract, ticker) in enumerate(valid_contracts, start=1):
        delta = getattr(ticker.modelGreeks, 'delta', 'N/A')
        gamma = getattr(ticker.modelGreeks, 'gamma', 'N/A')
        theta = getattr(ticker.modelGreeks, 'theta', 'N/A')
        vega = getattr(ticker.modelGreeks, 'vega', 'N/A')
        iv = getattr(ticker.modelGreeks, 'impliedVolatility', 'N/A')
        ask = ticker.ask if ticker.ask is not None else 'N/A'
        print(f"{i}. Strike: {contract.strike} | Δ: {delta} | Γ: {gamma} | θ: {theta} | ν: {vega} | IV: {iv} | Ask: {ask}")

    return valid_contracts
def fetch_candles(ib, symbol, duration, bar_size):
    contract = Stock(symbol, 'SMART', 'USD')
    bars = ib.reqHistoricalData(
        contract,
        endDateTime='',
        durationStr=duration,
        barSizeSetting=bar_size,
        whatToShow='TRADES',
        useRTH=True,
        formatDate=1
    )
    return util.df(bars)

def monitor_and_trade(ib, user_data, selected_contract, logger):
    bar_size = user_data['timeframe']
    duration = "2 D"
    entered = False
    entry_price = None

    while True:
        df = fetch_candles(ib, user_data['symbol'], duration, bar_size)
        last_close = df['close'].iloc[-1]
        logger.info("Last close: %.2f", last_close)
        print(f"Last close: {last_close:.2f}")

        market_price = ib.reqMktData(Stock(user_data['symbol'], 'SMART', 'USD'), '', False, False)
        ib.sleep(2)
        spot_price = float(market_price.last)
        logger.info("Current spot price: %.2f", spot_price)
        print(f"Current spot price: {spot_price:.2f}")

        if not entered:
            if user_data['option_type'] == 'call' and spot_price > user_data['entry_level']:
                logger.info("✅ Entry condition met for CALL. Preparing to place BUY order for %d contracts of %s", number_of_contracts, selected_contract.localSymbol)
                print(f"✅ Entry condition met for CALL. Preparing to place BUY order for {number_of_contracts} contracts of {selected_contract.localSymbol}")
            elif user_data['option_type'] == 'put' and spot_price < user_data['entry_level']:
                logger.info("✅ Entry condition met for PUT. Preparing to place BUY order for %d contracts of %s", number_of_contracts, selected_contract.localSymbol)
                print(f"✅ Entry condition met for PUT. Preparing to place BUY order for {number_of_contracts} contracts of {selected_contract.localSymbol}")
            else:
                time.sleep(15)
                continue

            ticker = ib.reqMktData(selected_contract, '', False, False)
            ib.sleep(2)
            bid = ticker.bid
            ask = ticker.ask
            mid_price = (bid + ask) / 2 if bid and ask else ask or bid
            logger.info("Initial option bid: %.2f, ask: %.2f, mid: %.2f", bid, ask, mid_price)
            print(f"Initial option bid: {bid:.2f}, ask: {ask:.2f}, mid: {mid_price:.2f}")

            # Calculate number of contracts to buy based on user capital
            number_of_contracts = int(user_data['capital'] / (ask * 100))
            logger.info("Number of contracts to buy: %d", number_of_contracts)
            print(f"Number of contracts to buy: {number_of_contracts}")

            for attempt in range(10):
                order = LimitOrder('BUY', number_of_contracts, mid_price)
                trade = ib.placeOrder(selected_contract, order)
                logger.info("Placing BUY LimitOrder at mid price: %.2f (Attempt %d)", mid_price, attempt + 1)
                print(f"Placing BUY LimitOrder at mid price: {mid_price:.2f} (Attempt {attempt + 1})")
                ib.sleep(5)
                if trade.isDone():
                    break
                ticker = ib.reqMktData(selected_contract, '', False, False)
                ib.sleep(2)
                bid = ticker.bid
                ask = ticker.ask
                mid_price = (bid + ask) / 2 if bid and ask else ask or bid
                logger.info("Updated option bid: %.2f, ask: %.2f, mid: %.2f", bid, ask, mid_price)
                print(f"Updated option bid: {bid:.2f}, ask: {ask:.2f}, mid: {mid_price:.2f}")

            entry_price = trade.fills[-1].execution.price if trade.fills else None
            if entry_price:
                logger.info("✅ Order filled at price: %.2f", entry_price)
                print(f"✅ Order filled at price: {entry_price:.2f}")
                entered = True
                logger.info("Trade entry complete. Monitoring for exit conditions (TP: %.2f, SL: %.2f)", user_data['take_profit'], user_data['stop_loss'])
                print(f"Trade entry complete. Monitoring for exit conditions (TP: {user_data['take_profit']:.2f}, SL: {user_data['stop_loss']:.2f})")
            else:
                logger.warning("⚠️ Order not filled after 10 attempts. Exiting.")
                print("⚠️ Order not filled after 10 attempts. Exiting.")
                return

            positions = ib.positions()
            held = any(pos.contract.conId == selected_contract.conId for pos in positions)

            if held:
                logger.info("✅ Position confirmed: contract is held in the account.")
                print("✅ Position confirmed: contract is held in the account.")
            else:
                logger.warning("⚠️ Position not found after order fill. It may have been closed or rejected.")
                print("⚠️ Position not found after order fill. It may have been closed or rejected.")
                return

        if entered:
            ticker = ib.reqMktData(selected_contract, '', False, False)
            ib.sleep(2)
            bid = ticker.bid
            ask = ticker.ask
            mid_price = (bid + ask) / 2 if bid and ask else ask or bid
            logger.info("Option bid: %.2f, ask: %.2f, mid: %.2f", bid, ask, mid_price)
            print(f"Option bid: {bid:.2f}, ask: {ask:.2f}, mid: {mid_price:.2f}")

            if spot_price >= user_data['take_profit']:
                logger.info("📈 Take profit condition met. Current spot price: %.2f >= TP: %.2f", spot_price, user_data['take_profit'])
                print(f"📈 Take profit condition met. Current spot price: {spot_price:.2f} >= TP: {user_data['take_profit']:.2f}")
            elif spot_price <= user_data['stop_loss']:
                logger.info("📉 Stop loss condition met. Current spot price: %.2f <= SL: %.2f", spot_price, user_data['stop_loss'])
                print(f"📉 Stop loss condition met. Current spot price: {spot_price:.2f} <= SL: {user_data['stop_loss']:.2f}")
            else:
                time.sleep(15)
                continue

            order = LimitOrder('SELL', number_of_contracts, mid_price)
            trade = ib.placeOrder(selected_contract, order)
            logger.info("Placing SELL LimitOrder at mid price: %.2f", mid_price)
            print(f"Placing SELL LimitOrder at mid price: {mid_price:.2f}")
            while not trade.isDone():
                ib.sleep(1)
            exit_price = trade.fills[-1].execution.price
            logger.info("✅ Exit order filled at price: %.2f", exit_price)
            print(f"✅ Exit order filled at price: {exit_price:.2f}")
            break

        time.sleep(15)
