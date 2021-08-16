from binance.client import Client
from time import sleep
import tkinter
from threading import Thread
from credentials import API_KEY, API_SECRET
from shared_functions import round_down, rgb2hex
from openpyxl import load_workbook
from binance import exceptions

FONT_LARGE = ("IBM Plex Sans", 17, "normal")
FONT_MID_LARGE = ("IBM Plex Sans", 14, "normal")
FONT_MEDIUM = ("IBM Plex Sans", 11, "normal")
FONT_SMALL = ("IBM Plex Sans", 8, "normal")

BG_COLOR = "#181A20"
LONG_COLOR = "#02C077"
SHORT_COLOR = "#F84960"

DEFAULT_FIAT_CURRENCY = "USDT"

class Trade():
    def __init__(self):
        self.trade_factor = 0.1
        self.closing_factor = 1
        self.order_book_num = 0

        self.root = tkinter.Tk()
        self.root.title("Trade Assister")
        self.root.geometry("+1290+200")
        self.root.resizable(width=False, height=False)
        self.root.configure(bg=BG_COLOR, padx=15)

        self.instruction = tkinter.Label(text="Enter crypto name:", font=FONT_MEDIUM, bg=BG_COLOR, fg="white")
        self.instruction.grid(pady=10)
        self.crypto_name_entry = tkinter.Entry(width=10, font=FONT_MEDIUM)
        self.crypto_name_entry.grid(pady=10)

        self.crypto_name_entry.bind("<Return>", self.initialize)

    def initialize(self, event):
        self.crypto_name = self.crypto_name_entry.get().upper()
        self.crypto_fullname = self.crypto_name + DEFAULT_FIAT_CURRENCY
        self.instruction.destroy()
        self.crypto_name_entry.destroy()

        try:
            self.client = Client(API_KEY, API_SECRET)
        except exceptions.BinanceAPIException:
            tkinter.Label(text="Time sync required", font=FONT_MEDIUM, bg=BG_COLOR, fg="white").grid(pady=10)
        
        exchange_info = self.client.futures_exchange_info()["symbols"]
        for item in exchange_info:
            if item["symbol"] == self.crypto_fullname:
                self.quantity_decimal_place = int(item["quantityPrecision"])
                break
        account_info = self.client.futures_account()
        for item in account_info["positions"]:
            if item["symbol"] == self.crypto_fullname:
                self.leverage = int(item["leverage"])
                break
        for item in account_info["assets"]:
            if item["asset"] == DEFAULT_FIAT_CURRENCY:
                self.usdt_index = (account_info["assets"].index(item))

        wb = load_workbook('Trade Record.xlsx')
        sheet = wb["Balance Record"]
        for cell in sheet["A"]:
            if cell.value == None:
                cell_num = int(str(cell).split(".")[1][1:-1]) - 1
                self.balance_before = float(sheet["B" + str(cell_num)].value)
                break

        symbol_label = tkinter.Label(text=self.crypto_fullname, font=FONT_LARGE, bg=BG_COLOR, fg="white")
        symbol_label.grid(columnspan=3)
        self.overall_profit_label = tkinter.Label(text="Overall Profit: 0.00%", font=FONT_MID_LARGE, bg=BG_COLOR, fg="white")
        self.overall_profit_label.grid(columnspan=3)
        self.position_label = tkinter.Label(text="Not in Position", font=FONT_LARGE, bg=BG_COLOR, fg="white")
        self.position_label.grid(columnspan=3)
        self.margin_input_label = tkinter.Label(text="Margin Input: nil", font=FONT_MID_LARGE, bg=BG_COLOR, fg="white")
        self.margin_input_label.grid(columnspan=3)
        self.profit_label = tkinter.Label(text="Profit: nil", font=FONT_MID_LARGE, bg=BG_COLOR, fg="white")
        self.profit_label.grid(columnspan=3)

        self.trade_factor_label = tkinter.Label(
            text="Trade Factor",
            font=FONT_SMALL,
            bg=BG_COLOR,
            fg="white")
        self.trade_factor_label.grid(column=0, row=5)
        self.trade_factor_display = tkinter.Label(
            text=str(self.trade_factor),
            font=FONT_SMALL,
            bg=BG_COLOR,
            fg="white")
        self.trade_factor_display.grid(column=1, row=5, sticky="w")
        self.trade_factor_entry = tkinter.Entry(width=4, font=FONT_SMALL)
        self.trade_factor_entry.bind("<Return>", self.update_trade_factor)
        self.trade_factor_entry.grid(column=2, row=5)

        self.closing_factor_label = tkinter.Label(
            text="Closing Factor",
            font=FONT_SMALL,
            bg=BG_COLOR,
            fg="white")
        self.closing_factor_label.grid(column=0, row=6)
        self.closing_factor_display = tkinter.Label(
            text=str(self.closing_factor),
            font=FONT_SMALL,
            bg=BG_COLOR,
            fg="white")
        self.closing_factor_display.grid(column=1, row=6, sticky="w")
        self.closing_factor_entry = tkinter.Entry(width=4, font=FONT_SMALL)
        self.closing_factor_entry.bind("<Return>", self.update_closing_factor)
        self.closing_factor_entry.grid(column=2, row=6)

        self.order_book_num_label = tkinter.Label(
            text="Order Book Number",
            font=FONT_SMALL,
            bg=BG_COLOR,
            fg="white")
        self.order_book_num_label.grid(column=0, row=7)
        self.order_book_num_display = tkinter.Label(
            text=str(self.order_book_num),
            font=FONT_SMALL,
            bg=BG_COLOR,
            fg="white")
        self.order_book_num_display.grid(column=1, row=7, sticky="w")
        self.order_book_num_entry = tkinter.Entry(width=4, font=FONT_SMALL)
        self.order_book_num_entry.bind("<Return>", self.update_order_book_num)
        self.order_book_num_entry.grid(column=2, row=7)

        self.command_label = tkinter.Label(
            text="Enter Command:", font=FONT_MEDIUM,
            bg=BG_COLOR,
            fg="white")
        self.command_label.grid(columnspan=3)
        self.command_entry = tkinter.Entry(width=10, font=FONT_MEDIUM)
        self.command_entry.bind("<Return>", self.run_command)
        self.command_entry.grid(pady=(5, 10), columnspan=3)

        update_info_thread = Thread(target=self.update_info, daemon=True)
        update_info_thread.start()
        update_client_thread = Thread(target=self.update_client, daemon=True)
        update_client_thread.start() 

    def update_trade_factor(self, event):
        trade_factor = self.trade_factor_entry.get()
        if trade_factor != "":
            try:
                self.trade_factor = float(trade_factor) / 100
                self.trade_factor_display.configure(text=str(self.trade_factor))
                self.trade_factor_entry.delete(0, "end")
            except ValueError:
                pass
    
    def update_closing_factor(self, event):
        closing_factor = self.closing_factor_entry.get()
        if closing_factor != "":
            try:
                self.closing_factor = float(closing_factor) / 100
                self.closing_factor_display.configure(text=str(self.closing_factor))
                self.closing_factor_entry.delete(0, "end")
            except ValueError:
                pass

    def update_order_book_num(self, event):
        order_book_num = self.order_book_num_entry.get()
        if order_book_num != "":
            try:
                self.order_book_num = int(order_book_num)
                self.order_book_num_display.configure(text=str(self.order_book_num))
                self.order_book_num_entry.delete(0, "end")
            except ValueError:
                pass

    def run_command(self, event):
        command = self.command_entry.get()
        if command == "b":
            self.enter_long()
        elif command == "s":
            self.enter_short()
        elif command == "cl":
            self.close_position()
        elif command == "cc":
            self.cancel_order()
        self.command_entry.delete(0, "end")

    def update_info(self):
        while True:
            balance = round(float(self.client.futures_account()["totalWalletBalance"]), 2)
            overall_profit = round((balance / self.balance_before - 1) * 100, 2)
            overall_profit_text = "Overall Profit: " + str(overall_profit) + "%"
            if overall_profit > 0:
                self.overall_profit_label.configure(text=overall_profit_text, fg=LONG_COLOR)
            elif overall_profit < 0:
                self.overall_profit_label.configure(text=overall_profit_text, fg=SHORT_COLOR)
            else:
                self.overall_profit_label.configure(text=overall_profit_text, fg="white")
            position_info = self.client.futures_position_information(symbol=self.crypto_fullname)[0]
            position_amount = float(position_info["positionAmt"])
            if position_amount == 0:
                self.position_label.configure(text="Not in Position", fg="white")
                self.profit_label.configure(text="Profit: nil", fg="white")
                self.margin_input_label.configure(text="Margin Input: nil", fg="white")
            else:
                # Profit
                self.profit = float(position_info["unRealizedProfit"])
                profit_float = float(self.profit)
                if position_amount > 0:
                    self.position_label.configure(text="Long", fg=LONG_COLOR)
                else:
                    self.position_label.configure(text="Short", fg=SHORT_COLOR)
                if profit_float > 0:
                    profit_percentage = round((float(self.profit) / balance) * 100, 2)
                    self.profit_label.configure(
                        text=f"Profit: ${round(self.profit, 2)} ({profit_percentage}%)",
                        fg=LONG_COLOR)
                elif profit_float < 0:
                    profit_percentage = round((float(self.profit) / balance) * 100, 2)
                    self.profit_label.configure(
                        text=f"Profit: -${round(abs(self.profit), 2)} ({profit_percentage}%)",
                        fg=SHORT_COLOR)
                else:
                    self.profit_label.configure(text="Profit: $0.00", fg="white")
                # Margin input
                available_balance = round(float(self.client.futures_account()["assets"][self.usdt_index]["availableBalance"]), 2)
                margin_input_ratio = 1 - available_balance / balance
                # Preventing possible error of rgb2hex function
                if margin_input_ratio < 0:
                    margin_input_ratio = 0
                elif margin_input_ratio > 1:
                    margin_input_ratio = 1
                margin_input_percentage = round(margin_input_ratio * 100, 2)
                self.margin_input_label.configure(text="Margin Input: " + str(margin_input_percentage) + "%")
                margin_GB = int(255 * (1 - margin_input_ratio))
                margin_color = rgb2hex(255, margin_GB, margin_GB)
                self.margin_input_label.configure(fg=margin_color) 
            sleep(0.5)

    def enter_long(self):
        balance = float(self.client.futures_account()["assets"][self.usdt_index]["walletBalance"])
        order_book = self.client.futures_order_book(symbol=self.crypto_fullname, limit=5)
        entering_price = float(order_book["bids"][self.order_book_num][0])
        buy_amount = round_down((balance * self.leverage * self.trade_factor) / entering_price, self.quantity_decimal_place)
        self.client.futures_create_order(
            symbol=self.crypto_fullname,
            side="BUY",
            type="LIMIT",
            timeInForce="GTC",
            quantity=buy_amount,
            price=entering_price)

    def enter_short(self):
        balance = float(self.client.futures_account()["assets"][self.usdt_index]["walletBalance"])
        order_book = self.client.futures_order_book(symbol=self.crypto_fullname, limit=5)
        entering_price = float(order_book["asks"][self.order_book_num][0])
        sell_amount = round_down((balance * self.leverage * self.trade_factor) / entering_price, self.quantity_decimal_place)
        self.client.futures_create_order(
            symbol=self.crypto_fullname,
            side="SELL",
            type="LIMIT",
            timeInForce="GTC",
            quantity=sell_amount,
            price=entering_price)

    def close_position(self):
        position_amount = float(self.client.futures_position_information(symbol=self.crypto_fullname)[0]["positionAmt"])
        closing_amount = abs(round(position_amount * self.closing_factor, self.quantity_decimal_place))
        if position_amount != 0:
            if position_amount > 0:
                closing_price = float(self.client.futures_order_book(symbol=self.crypto_fullname, limit=5)["asks"][self.order_book_num][0])
                buy_or_sell = "SELL"
            elif position_amount < 0:
                closing_price = float(self.client.futures_order_book(symbol=self.crypto_fullname, limit=5)["bids"][self.order_book_num][0])
                buy_or_sell = "BUY"
            self.client.futures_create_order(
                symbol=self.crypto_fullname,
                side=buy_or_sell,
                type="LIMIT",
                timeInForce="GTC",
                quantity=closing_amount,
                price=closing_price)

    def cancel_order(self):
        self.client.futures_cancel_all_open_orders(symbol=self.crypto_fullname)

    def update_client(self):
        while True:
            sleep(1800)
            self.client = Client(API_KEY, API_SECRET)

    def run(self):
        self.root.mainloop()

app = Trade()
app.run()
