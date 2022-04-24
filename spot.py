import binance.spot
import binance.error
import tkinter
from tkinter import Event, messagebox
from binance.websocket.spot.websocket_client import SpotWebsocketClient
from constants import *
from datetime import datetime
from openpyxl import load_workbook
from threading import Thread
from time import sleep, time

class Spot():
    def __init__(self, api_key: str, api_secret: str, root: tkinter.Tk) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = binance.spot.Spot(api_key, api_secret)
        self.my_listen_key = self.client.new_listen_key()["listenKey"]

        self.root = root

    def initialize(self, symbol: str, crypto: str, fiat: str):
        self.symbol = symbol
        self.crypto = crypto
        self.fiat = fiat

        self.trading_currency: str = fiat
        self.trading_amount: float = 10
        self.order_book_num: int = 0

        self.wb = load_workbook(RECORD_FILE_NAME)

        filters = self.client.exchange_info(symbol=self.symbol)["symbols"][0]["filters"]

        self.fiat_decimal_place: int = filters[0]["tickSize"].count("0")
        self.crypto_decimal_place: int = filters[2]["stepSize"].count("0")

        self.curr_price = float(self.client.ticker_price(symbol=self.symbol)["price"])
        self.update_balance(None)

        sheet = self.wb["Spot"]
        if sheet["A2"].value == None: # if the user is using this app for the first time
            self.initialize_record()

        self.get_currency_actions()

        row_num = len(list(sheet.rows))
        if self.fiat in {"BUSD", "USDT", "USDC"}:
            self.balance_before = float(sheet["B"+str(row_num)].value)
        else:
            exchange_rate = float(self.client.ticker_price(symbol=self.fiat+"BUSD")["price"])
            self.balance_before = round(float(sheet["B"+str(row_num)].value)/exchange_rate, 2)

        symbol_label = tkinter.Label(text=self.symbol, font=FONT_LARGE, bg=BG_COLOR, fg="white")
        symbol_label.grid(columnspan=3)

        self.profit_label = tkinter.Label(text="Profit: $0.00 (0.00%)", font=FONT_MID_LARGE, bg=BG_COLOR, fg="white")
        self.profit_label.grid(columnspan=3)

        self.total_balance_label = tkinter.Label(text=f"Estimated Balance: {self.curr_total_balance} {self.fiat}", font=FONT_MID_LARGE, bg=BG_COLOR, fg="white")
        self.total_balance_label.grid(columnspan=3)

        trading_amount_row_num = 4
        trading_amount_label = tkinter.Label(text="Trading Amount", font=FONT_SMALL, bg=BG_COLOR, fg="white")
        trading_amount_label.grid(column=0, row=trading_amount_row_num)
        self.trading_amount_display = tkinter.Label(text=f"{self.trading_amount} {self.trading_currency}", font=FONT_SMALL, bg=BG_COLOR, fg="white")
        self.trading_amount_display.grid(column=1, row=trading_amount_row_num, sticky="w")
        trading_amount_entry = tkinter.Entry(width=4, font=FONT_SMALL)
        trading_amount_entry.bind("<Return>", self.update_trading_amount)
        trading_amount_entry.grid(column=2, row=trading_amount_row_num)

        order_book_row_num = 5
        order_book_num_label = tkinter.Label(text="Order Book Number", font=FONT_SMALL, bg=BG_COLOR, fg="white")
        order_book_num_label.grid(column=0, row=order_book_row_num)
        self.order_book_num_display = tkinter.Label(text=self.order_book_num, font=FONT_SMALL, bg=BG_COLOR, fg="white")
        self.order_book_num_display.grid(column=1, row=order_book_row_num, sticky="w")
        order_book_num_entry = tkinter.Entry(width=4, font=FONT_SMALL)
        order_book_num_entry.bind("<Return>", self.update_order_book_num)
        order_book_num_entry.grid(column=2, row=order_book_row_num)

        self.status_label = tkinter.Label(text="Start Trading by Entering a Command:", font=FONT_MEDIUM, bg=BG_COLOR, fg="white")
        self.status_label.grid(columnspan=3)

        command_entry = tkinter.Entry(width=10, font=FONT_MEDIUM)
        command_entry.bind("<Return>", self.run_command)
        command_entry.grid(pady=(5, 10), columnspan=3)

        record_balance_button = tkinter.Button(text="Record balance", font=FONT_MEDIUM, command=self.record_balance)
        record_balance_button.grid(pady=10, columnspan=3)

        update_info_thread = Thread(target=self.update_info, daemon=True)
        update_info_thread.start()
        self.start_websockets()

    def update_trading_amount(self, event):
        trading_amount = event.widget.get()
        if trading_amount != "":
            try:
                self.trading_amount = float(trading_amount)
                self.trading_amount_display.config(text=f"{self.trading_amount} {self.trading_currency}")
                event.widget.delete(0, "end")
                self.status_label.config(text="Trading Amount Updated.")
            except ValueError:
                self.status_label.config(text="ValueError. Please enter a number.")


    def update_order_book_num(self, event: tkinter.Event):
        order_book_num = event.widget.get()
        if order_book_num != "":
            try:
                self.order_book_num = int(order_book_num)
                self.order_book_num_display.config(text=self.order_book_num)
                event.widget.delete(0, "end")
                self.status_label.config(text="Order Book Number Updated.")
            except ValueError:
                self.status_label.config(text="ValueError. Please enter a number.")

    def run_command(self, event: Event):
        command: str = event.widget.get()
        if command == "b":
            self.buy()
        elif command == "s":
            self.sell()
        elif command == "t":
            self.change_trading_currency()
        elif command == "c":
            self.cancel_order(1)
        elif command.startswith("c"):
            self.cancel_order(command[2:])
        else:
            self.status_label.config(text="Please enter a valid command")
        event.widget.delete(0, "end")

    def buy(self):
        buying_price = float(self.bids_order_book[self.order_book_num][0])
        if self.trading_currency == self.fiat:
            buying_quantity = round(self.trading_amount/buying_price, self.crypto_decimal_place)
        else:
            buying_quantity = round(self.trading_amount, self.crypto_decimal_place)
        try:
            self.status_label.config(text="Placing a buy order...")
            self.client.new_order(
                symbol=self.symbol,
                side="BUY",
                type="LIMIT",
                timeInForce="GTC",
                price=buying_price,
                quantity=buying_quantity)
        except binance.error.ClientError as client_error:
            self.status_label.config(text=client_error.error_message)
        except binance.error.ServerError as server_error:
            self.status_label.config(text=server_error.message)
        else:
            self.status_label.config(text=f"Buy order placed to buy {buying_quantity} {self.fiat} at ${buying_price}")

    def sell(self):
        selling_price = float(self.asks_order_book[self.order_book_num][0])
        if self.trading_currency == self.fiat:
            selling_quantity = round(self.trading_amount/selling_price, self.crypto_decimal_place)
        else:
            selling_quantity = round(self.trading_amount, self.crypto_decimal_place)
        try:
            self.status_label.config(text="Placing a sell order...")
            self.client.new_order(
                symbol=self.symbol,
                side="SELL",
                type="LIMIT",
                timeInForce="GTC",
                price=selling_price,
                quantity=selling_quantity)
        except binance.error.ClientError as client_error:
            self.status_label.config(text=client_error.error_message)
        except binance.error.ServerError as server_error:
            self.status_label.config(text=server_error.message)
        else:
            self.status_label.config(text=f"Sell order placed to sell {selling_quantity} {self.fiat} at ${selling_price}")

    def change_trading_currency(self):
        if self.trading_currency == self.fiat:
            self.trading_currency = self.crypto
        else:
            self.trading_currency = self.fiat
        self.trading_amount_display.config(text=f"{self.trading_amount} {self.trading_currency}")
        self.status_label.config(text="Trading currency changed")

    def cancel_order(self, order_num):
        try:
            order_num = int(order_num)
        except ValueError:
            self.status_label.config(text="Invalid command. Please check your command.")
        else:
            open_orders = self.client.get_open_orders(self.symbol)
            order_id = open_orders[len(open_orders)-order_num]["orderId"]
            response = self.client.cancel_order(symbol=self.symbol, orderId=order_id)
            if response["status"] == "CANCELED":
                self.status_label.config(text=f"Order {order_num} cancelled")
            else:
                self.status_label.config(text=f"Error occured while cancelling order {order_num}")

    def update_balance(self, msg):
        self.fiat_balance = ""
        self.crypto_balance = ""

        try:
            account_info = self.client.account()
        except binance.error.ClientError as client_error:
            self.status_label.config(text=client_error.error_message)
        except binance.error.ServerError as server_error:
            self.status_label.config(text=server_error.message)

        for item in account_info["balances"]:
            if item["asset"] == self.fiat:
                self.fiat_balance = float(item["free"])
            elif item["asset"] == self.crypto:
                self.crypto_balance = float(item["free"])
            if (self.fiat_balance != "") and (self.crypto_balance != ""):
                break

        try:
            open_orders = self.client.get_open_orders(symbol=self.symbol)
        except binance.error.ClientError as client_error:
            self.status_label.config(text=client_error.error_message)
        except binance.error.ServerError as server_error:
            self.status_label.config(text=server_error.message)

        for order in open_orders:
            self.crypto_balance += (float(order["origQty"]) - float(order["executedQty"]))

        self.curr_total_balance = round(self.fiat_balance + self.crypto_balance*self.curr_price, 2)

    def get_currency_actions(self):
        sheet = self.wb["Spot"]
        last_access_time = int(sheet[LAST_ACCESS_DATE_CELL].value)
        sheet[LAST_ACCESS_DATE_CELL] = round(time() * 1000)
        total_logs = self.get_deposit_history(last_access_time) + self.get_transfer_history(last_access_time) + self.get_convert_history(last_access_time)
        log_msg = ""
        for log in total_logs:
            log_msg += log + ". "
        return log_msg

    def get_convert_history(self, last_access_time):
        logs = []
        try:
            convert_hist = self.client.convert_trade_history(startTime=last_access_time, endTime=round(time()*1000))["list"]
        except binance.error.ClientError as client_error:
            self.status_label.config(text=client_error.error_message)
        except binance.error.ServerError as server_error:
            self.status_label.config(text=server_error.message)
        for hist in convert_hist:
            from_asset = hist["fromAsset"]
            to_asset = hist["toAsset"]
            if hist["orderStatus"] == "SUCCESS" and ((self.crypto in {from_asset, to_asset}) or (self.flat in {from_asset, to_asset})):
                from_amount = hist["fromAmount"]
                to_amount = hist["toAmount"]

                logs.append(f"Converted {from_amount} {from_asset} to {to_amount} {to_asset}")
        return logs

    def get_transfer_history(self, last_access_time):
        logs = []
        try:
            spot_to_margin = self.client.user_universal_transfer_history(type="MAIN_MARGIN", startTime=last_access_time, endTime=round(time()*1000))
            margin_to_spot = self.client.user_universal_transfer_history(type="MARGIN_MAIN", startTime=last_access_time, endTime=round(time()*1000))
        except binance.error.ClientError as client_error:
            self.status_label.config(text=client_error.error_message)
        except binance.error.ServerError as server_error:
            self.status_label.config(text=server_error.message)
        if spot_to_margin["total"] > 0:
            spot_to_margin = spot_to_margin["rows"]
            for hist in spot_to_margin:
                asset = hist["asset"]
                if asset == self.fiat or asset == self.crypto:
                    amount = hist["amount"]
                    logs.append(f"{amount} {asset} transferred from spot to cross margin account")
        if margin_to_spot["total"] > 0:
            margin_to_spot = margin_to_spot["rows"]
            for hist in margin_to_spot:
                asset = hist["asset"]
                if asset == self.fiat or asset == self.crypto:
                    amount = hist["amount"]
                    logs.append(f"{amount} {asset} transferred from cross margin to spot account")
        return logs

    def get_deposit_history(self, last_access_time):
        logs = []
        try:
            dep_hist = self.client.fiat_order_history(transactionType=0, beginTime=last_access_time, endTime=round(time()*1000))["data"]
            withdraw_hist = self.client.fiat_order_history(transactionType=1, beginTime=last_access_time, endTime=round(time()*1000))["data"]
        except binance.error.ClientError as client_error:
            self.status_label.config(text=client_error.error_message)
        except binance.error.ServerError as server_error:
            self.status_label.config(text=server_error.message)

        for deposit in dep_hist:
            fiat_currency = deposit["fiatCurrency"]
            if fiat_currency == self.fiat:
                amount = float(deposit["amount"]) - float(deposit["totalFee"])
                logs.append(f"Deposited {amount} {fiat_currency}")

        for withdraw in withdraw_hist:
            fiat_currency = withdraw["fiatCurrency"]
            if fiat_currency == self.fiat:
                amount = float(withdraw["amount"]) - float(withdraw["totalFee"])
                logs.append(f"Withdrew {amount} {fiat_currency}")
        return logs

    def initialize_record(self):
        sheet = self.wb["Spot"]
        sheet["A2"].number_format = SPOT_MARGIN_FORMATS[0]
        sheet["A2"] = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        sheet["B2"].number_format = SPOT_MARGIN_FORMATS[1]
        if self.fiat in {"BUSD", "USDT", "USDC"}:
            sheet["B2"] = self.curr_total_balance
        else:
            exchange_rate = float(self.client.ticker_price(symbol=self.fiat+"BUSD")["price"])
            sheet["B2"] = round(self.curr_total_balance*exchange_rate, 2)
        sheet[LAST_ACCESS_DATE_CELL] = round(time() * 1000)
        self.wb.save(RECORD_FILE_NAME)

    def record_balance(self, event):
        will_proceed = messagebox.askokcancel(title="Binance Trading Assister by soobakjonmat", message="Do you want to record current balance?")
        if not will_proceed:
            return
        sheet = self.wb["Spot"]
        row_num = str(len(list(sheet.rows)) + 1)
        sheet["A"+row_num].number_format = SPOT_MARGIN_FORMATS[0]
        sheet["A"+row_num] = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        sheet["B"+row_num].number_format = SPOT_MARGIN_FORMATS[1]
        if self.fiat in {"BUSD", "USDT", "USDC"}:
            sheet["B"+row_num] = self.curr_total_balance
        else:
            exchange_rate = float(self.client.ticker_price(symbol=self.fiat+"BUSD")["price"])
            sheet["B"+row_num] = round(self.curr_total_balance*exchange_rate, 2)
        self.balance_before = self.curr_total_balance

        sheet["D"+row_num] = self.get_currency_actions()
        self.wb.save(RECORD_FILE_NAME)

    def start_websockets(self):
        try:
            self.ws_client = SpotWebsocketClient()
            self.ws_client.daemon = True
            self.ws_client.start()
            self.ws_client.mini_ticker(id=0, symbol=self.symbol, callback=self.update_price)
            self.ws_client.partial_book_depth(id=1, symbol=self.symbol, level=10, speed=1000, callback=self.update_order_book)
            self.ws_client.user_data(id=2, listen_key=self.my_listen_key, callback=self.update_balance)
        except binance.error.ClientError as client_error:
            self.status_label.config(text=client_error.error_message)
        except binance.error.ServerError as server_error:
            self.status_label.config(text=server_error.message)

    def update_price(self, msg):
        if "c" in msg:
            self.curr_price = float(msg["c"])
            self.curr_total_balance = round(self.fiat_balance + self.crypto_balance*self.curr_price, 2)
            self.total_balance_label.config(text=f"Estimated Balance: {self.curr_total_balance} {self.fiat}")
        else:
            return

    def update_order_book(self, msg):
        if "lastUpdateId" in msg:
            self.bids_order_book = msg["bids"]
            self.asks_order_book = msg["asks"]
        else:
            return

    def update_profit(self):
        profit = self.curr_total_balance - self.balance_before
        if profit > 0:
            profit_percentage = round((float(profit) * 100 / self.curr_total_balance), 2)
            self.profit_label.config(
                text=f"Profit: ${round(profit, 2)} ({profit_percentage}%)",
                fg=PROFIT_COLOR)
        elif profit < 0:
            profit_percentage = round((float(profit) * 100 / self.curr_total_balance), 2)
            self.profit_label.config(
                text=f"Profit: -${round(abs(profit), 2)} ({profit_percentage}%)",
                fg=LOSS_COLOR)
        else:
            self.profit_label.config(text="Profit: $0.00 (0.00%)", fg="white")

    def update_info(self):
        while 1:
            self.update_profit()
            sleep(1)
