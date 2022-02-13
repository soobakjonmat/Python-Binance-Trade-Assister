import tkinter
from openpyxl import load_workbook
import binance.spot
import binance.futures
from spot import Spot
from margin import Margin
import binance.error
from constants import *

api_key = ""
api_secret = ""

class App():
    def __init__(self) -> None:
        self.root = tkinter.Tk()
        self.root.title("Binance Trading Assister by soobakjonmat")
        self.root.geometry("+1150+200")
        self.root.configure(bg=BG_COLOR, padx=15)

        temp = tkinter.Label(text="Choose the Trading Mode:", font=FONT_LARGE, bg=BG_COLOR, fg="white")
        temp.grid(columnspan=2, pady=10)

        temp = tkinter.Button(text="Spot", font=FONT_MEDIUM)
        temp.bind("<Button-1>", self.check_API_info)
        temp.grid(column=0, row=1, pady=10)

        temp = tkinter.Button(text="Margin", font=FONT_MEDIUM, command=self.check_API_info)
        temp.config(state="disabled") # delete this after completing margin.py
        temp.grid(column=1, row=1, pady=10)

        
    def check_API_info(self, event: tkinter.Event):
        self.status_label = tkinter.Label(text="Checking API Info...", font=FONT_MEDIUM, bg=BG_COLOR, fg="white")
        self.status_label.grid(pady=10)

        wb = load_workbook(EXCEL_FILE_NAME)
        sheet = wb["API Info"]
        api_key = sheet[API_KEY_CELL].value
        api_secret = sheet[API_SECRET_CELL].value

        self.trading_mode = event.widget["text"]
        try:
            match self.trading_mode:
                case "Spot":
                    self.spot = Spot(api_key, api_secret, self.root)
                    self.spot.client.account()
                case "Margin":
                    self.margin = Margin(api_key, api_secret, self.root)
                    self.margin.client.account()
        except binance.error.ClientError as c_error:
            widgets = self.root.winfo_children()
            for widget in widgets:
                widget.destroy()
            self.show_client_error_message(c_error)
            tkinter.Label(text="Quit and try again", font=FONT_MEDIUM, background=BG_COLOR).grid(pady=10)
        except binance.error.ServerError as server_error:
            self.show_server_error_message(server_error)

        else:
            widgets = self.root.winfo_children()
            for widget in widgets:
                widget.destroy()
            self.create_currency_name_check()

    def create_currency_name_check(self):
        temp = tkinter.Label(text="Enter the name of the cryptocurrency (e.g. BTC):", font=FONT_MEDIUM, bg=BG_COLOR, fg="white")
        temp.grid(pady=(10, 0))

        self.crypto_name_entry = tkinter.Entry(width=10, font=FONT_MEDIUM)
        self.crypto_name_entry.grid(pady=(0, 10))

        temp = tkinter.Label(text="Enter the name of the fiat currency (e.g. USDT):", font=FONT_MEDIUM, bg=BG_COLOR, fg="white")
        temp.grid(pady=(10, 0))

        self.fiat_name_entry = tkinter.Entry(width=10, font=FONT_MEDIUM)
        self.fiat_name_entry.grid(pady=(0, 10))
        self.fiat_name_entry.bind("<Return>", self.test_currency_name)

        self.submit_button = tkinter.Button(text="Submit", font=FONT_MEDIUM, command=self.test_currency_name)
        self.submit_button.grid(pady=10)

        self.status_label = tkinter.Label(text="", font=FONT_SMALL, bg=BG_COLOR, fg="white")
        self.status_label.grid(pady=10)

    def test_currency_name(self):
        self.status_label.config(text="Checking Symbol Name...")
        self.root.update()
        self.submit_button.config(state="disabled")
        self.fiat = self.fiat_name_entry.get().upper()
        self.crypto = self.crypto_name_entry.get().upper()
        self.symbol = self.crypto + self.fiat
        self.fiat_name_entry.delete(0, 'end')
        self.crypto_name_entry.delete(0, 'end')
        
        try:
            match self.trading_mode:
                case "Spot":
                    self.spot.client.avg_price(self.symbol)
                case "Margin":
                    self.margin.client.ticker_price(self.symbol)
        except (binance.error.ClientError) as e:
            self.status_label.config(text=f"{e.error_message} Please check the symbol name and try again.")
            self.submit_button.config(state="normal")
        except (binance.error.ParameterRequiredError) as e:
            self.status_label.config(text="Please enter a symbol name and try again.")
            self.submit_button.config(state="normal")
        else:
            widgets = self.root.winfo_children()
            for widget in widgets:
                widget.destroy()
            match self.trading_mode:
                case "Spot":
                    self.spot.initialize(self.symbol, self.crypto, self.fiat)
                case "Margin":
                    self.margin.initialize(self.symbol, self.crypto, self.fiat)

    def show_client_error_message(self, client_error: binance.error.ClientError):
        tkinter.Label(text=client_error.error_code, font=FONT_MEDIUM, bg=BG_COLOR, fg="white").grid(pady=10)
        tkinter.Label(text=client_error.error_message, font=FONT_MEDIUM, bg=BG_COLOR, fg="white").grid(pady=10)

    def show_server_error_message(self, server_error: binance.error.ServerError):
        tkinter.Label(text=server_error.status_code, font=FONT_MEDIUM, bg=BG_COLOR, fg="white").grid(pady=10)
        tkinter.Label(text=server_error.message, font=FONT_MEDIUM, bg=BG_COLOR, fg="white").grid(pady=10)

if __name__ == "__main__":
    app = App()
    app.root.mainloop()