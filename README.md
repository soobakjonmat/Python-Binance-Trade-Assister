# Binance Trading Assister

## Preview
<img src="images/preview1.png"/>
<img src="images/preview2.png"/>
<img src="images/preview3.png"/>
<img src="images/preview4.png"/>

## Foreword
This application was made to enable trading on binance using only keyboard.

Margin Trading is not supported yet.

## Set Up
1. Install the IBM Plex Sans font on your computer if you don't have it already installed, by selecting all the .ttf files in IBM_Plex_Sans folder and pasting them into "C:\Windows\Fonts"
2. Run trade_assister.py to start.

## Assumptions
- The user uses only one crypto pair for trading
- The user's assets are contained only in Spot and Margin Accounts.

## Additional Information
- The base fiat currency used in Record.xlsx is BUSD
- Record.xlsx shows your overall trading history

### Commands
- b - Buy
- s - Sell
- t - Change trading currency between fiat and crypto
- c {1 ~ number of open orders} - Cancel an order. For example, "c 1" or "c" will cancel the most recently created order and "c {number of current open orders}" will cancel the oldest order.

To update:
- Trading Amount - Enter a number
- Order Book Number - Enter number between (0 ~ 9)
