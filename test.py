from ib_insync import *

# Connect to TWS or IB Gateway
ib = IB()
ib.connect('127.0.0.1', 7496, clientId=1)

# Print account information
account_summary = ib.accountSummary()
print(account_summary)

ib.disconnect()