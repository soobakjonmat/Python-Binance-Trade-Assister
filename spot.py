import binance.spot
import binance.error
import tkinter
from tkinter import messagebox
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

        self.wb = load_workbook(EXCEL_FILE_NAME)

        filters = self.client.exchange_info(symbol=self.symbol)["symbols"][0]["filters"]

        self.fiat_decimal_place: int = filters[0]["tickSize"].count("0")
        self.crypto_decimal_place: int = filters[2]["stepSize"].count("0")

        self.curr_price = float(self.client.ticker_price(symbol=self.symbol)["price"])
        self.update_balance(None)

        symbol_label = tkinter.Label(
            text=self.symbol,
            font=FONT_LARGE,
            bg=BG_COLOR,
            fg="white")
        symbol_label.grid(columnspan=3)

        sheet = self.wb["Spot"]
        if sheet["A2"].value == None: # if the user is using this app for the first time
            self.initialize_record()

        self.update_total_fiat_deposit_record()

        # update balance before
        row_num = len(list(sheet.rows))
        self.balance_before = sheet["B"+str(row_num)].value

        self.profit_label = tkinter.Label(
            text="",
            font=FONT_MID_LARGE,
            bg=BG_COLOR,
            fg="white")
        self.profit_label.config(text="Profit: $0.00 (0.00%)", fg="white")
        self.profit_label.grid(columnspan=3)

        trading_amount_row_num = 3
        trading_amount_label = tkinter.Label(
            text="Trade Factor",
            font=FONT_SMALL,
            bg=BG_COLOR,
            fg="white")
        trading_amount_label.grid(column=0, row=trading_amount_row_num)
        self.trading_amount_display = tkinter.Label(
            text=f"{self.trading_amount} {self.trading_currency}",
            font=FONT_SMALL,
            bg=BG_COLOR,
            fg="white")
        self.trading_amount_display.grid(column=1, row=trading_amount_row_num, sticky="w")
        trading_amount_entry = tkinter.Entry(width=4, font=FONT_SMALL)
        trading_amount_entry.bind("<Return>", self.update_trading_amount)
        trading_amount_entry.grid(column=2, row=trading_amount_row_num)

        order_book_row_num = 4
        order_book_num_label = tkinter.Label(
            text="Order Book Number",
            font=FONT_SMALL,
            bg=BG_COLOR,
            fg="white")
        order_book_num_label.grid(column=0, row=order_book_row_num)
        self.order_book_num_display = tkinter.Label(
            text=self.order_book_num,
            font=FONT_SMALL,
            bg=BG_COLOR,
            fg="white")
        self.order_book_num_display.grid(column=1, row=order_book_row_num, sticky="w")
        order_book_num_entry = tkinter.Entry(width=4, font=FONT_SMALL)
        order_book_num_entry.bind("<Return>", self.update_order_book_num)
        order_book_num_entry.grid(column=2, row=order_book_row_num)

        self.status_label = tkinter.Label(
            text="Start Trading by Entering a Command:", font=FONT_MEDIUM,
            bg=BG_COLOR,
            fg="white")
        self.status_label.grid(columnspan=3)

        command_entry = tkinter.Entry(width=10, font=FONT_MEDIUM)
        command_entry.bind("<Return>", self.run_command)
        command_entry.grid(pady=(5, 10), columnspan=3)

        record_balance_button = tkinter.Button(
            text="Record balance",
            font=FONT_MEDIUM,
            command=self.record_balance
        )
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

    def run_command(self, event):
        command = event.widget.get()
        match command:
            case "b":
                self.buy()
            case "s":
                self.sell()
            case "c":
                self.change_trading_currency()
            case _:
                self.status_label.config(text="Please enter a valid command")
        event.widget.delete(0, "end")

    def change_trading_currency(self):
        if self.trading_currency == self.fiat:
            self.trading_currency = self.crypto
        else:
            self.trading_currency = self.fiat
        self.trading_amount_display.config(text=f"{self.trading_amount} {self.trading_currency}")
        self.status_label.config(text="Trading currency changed")


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
            self.status_label.config(text=f"Buy order placed to buy {buying_quantity}{self.fiat} at ${buying_price}")

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
            self.status_label.config(text=f"Sell order placed to sell {selling_quantity}{self.fiat} at ${selling_price}")

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

    def update_total_fiat_deposit_record(self):
        sheet = self.wb["Spot"]
        last_access_time = int(sheet[LAST_ACCESS_DATE_CELL].value)
        sheet[LAST_ACCESS_DATE_CELL] = round(time() * 1000)
        
        total_deposit = 0
        try:
            dep_hist = self.client.fiat_order_history(transactionType=0, beginTime=last_access_time, endTime=round(time()*1000))["data"]
            withdraw_hist = self.client.fiat_order_history(transactionType=1, beginTime=last_access_time, endTime=round(time()*1000))["data"]
        except binance.error.ClientError as client_error:
            self.status_label.config(text=client_error.error_message)
        except binance.error.ServerError as server_error:
            self.status_label.config(text=server_error.message)

        for deposit in dep_hist:
            total_deposit += float(deposit["amount"])
            total_deposit -= float(deposit["totalFee"])

        for withdraw in withdraw_hist:
            total_deposit -= float(withdraw["amount"])
            total_deposit -= float(withdraw["totalFee"])

        if total_deposit != 0:
            sheet[TOTAL_DEPOSIT_CELL] = round(total_deposit, 2)
        self.wb.save(EXCEL_FILE_NAME)

        self.total_fiat_deposit = sheet[TOTAL_DEPOSIT_CELL].value

    def initialize_record(self):
        sheet = self.wb["Spot"]
        sheet["A2"] = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        sheet["B2"] = self.curr_total_balance
        sheet[TOTAL_DEPOSIT_CELL] = 0
        sheet[LAST_ACCESS_DATE_CELL] = round(time() * 1000)
        self.wb.save(EXCEL_FILE_NAME)

    def record_balance(self, event):
        will_proceed = messagebox.askokcancel(title="Binance Trading Assister by soobakjonmat", message="Do you want to record current balance?")
        if not will_proceed:
            return
        sheet = self.wb["Spot"]
        row_num = len(list(sheet.rows)) + 1
        sheet["A"+str(row_num)] = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        sheet["B"+str(row_num)] = self.curr_total_balance
        self.balance_before = self.curr_total_balance
        self.wb.save(EXCEL_FILE_NAME)

    def start_websockets(self):
        try:
            self.ws_client = SpotWebsocketClient()
            self.ws_client.daemon = True
            self.ws_client.start()
            self.ws_client.mini_ticker(id=0, symbol=self.symbol, callback=self.update_price)
            self.ws_client.partial_book_depth(id=1, symbol=self.symbol, level=5, speed=1000, callback=self.update_order_book)
            self.ws_client.user_data(id=2, listen_key=self.my_listen_key, callback=self.update_balance)
        except binance.error.ClientError as client_error:
            self.status_label.config(text=client_error.error_message)
        except binance.error.ServerError as server_error:
            self.status_label.config(text=server_error.message)

    def update_price(self, msg):
        if "c" in msg:
            self.curr_price = float(msg["c"])
            self.curr_total_balance = round(self.fiat_balance + self.crypto_balance*self.curr_price, 2)
        else:
            return

    def update_order_book(self, msg):
        if "lastUpdateId" in msg:
            self.bids_order_book = msg["bids"]
            self.asks_order_book = msg["asks"]
        else:
            return

    def update_profit(self):
        profit = self.curr_total_balance - self.balance_before - self.total_fiat_deposit
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
