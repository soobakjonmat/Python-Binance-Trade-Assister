from binance.client import Client
from credentials import API_KEY, API_SECRET
from shared_functions import test_runtime

client = Client(API_KEY, API_SECRET)

def create_test_order():
    balance = float(client.futures_account()["totalWalletBalance"])
    test_price = float(client.futures_order_book(symbol="BTCUSDT", limit=5)["bids"][1][0])
    test_amount = round(balance / test_price)
    print(f"Placing a test order")
    response = client.create_test_order(
        symbol="BTCUSDT",
        side="BUY",
        type="LIMIT",
        timeInForce="GTC",
        quantity=1,
        price=test_price)
    print("Request Processed")

test_runtime(5, 5, create_test_order)