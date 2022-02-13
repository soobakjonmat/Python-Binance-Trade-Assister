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


class Margin():
    def __init__(self, api_key: str, api_secret: str, root: tkinter.Tk) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = binance.spot.Spot(api_key, api_secret)
        
        self.root = root

    def initialize(self, symbol: str, crypto: str, fiat: str):
        self.symbol = symbol
        self.crypto = crypto
        self.fiat = fiat