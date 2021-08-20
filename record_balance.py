from binance.client import Client
from credentials import API_KEY, API_SECRET
from openpyxl import load_workbook
from datetime import date

DEFAULT_FIAT_CURRENCY = ""
text_file_path = "/Users/Isac/Desktop/Programming_stuff/DEFAULT_FIAT_CURRENCY.txt"
with open(text_file_path) as file:
    text = file.read()
    DEFAULT_FIAT_CURRENCY = text

client = Client(API_KEY, API_SECRET)
account_info = client.futures_account()
fiat_index = 0
for item in account_info["assets"]:
    if item["asset"] == DEFAULT_FIAT_CURRENCY:
        fiat_index = (account_info["assets"].index(item))

excel_file_path = "/Users/Isac/Desktop/Programming_stuff/Trade Record.xlsx"
current_date = date.today().isoformat()
wb = load_workbook(excel_file_path)
sheet = wb["Balance Record"]

for cell in sheet["A"]:
    if cell.value == None:
        row_num = int(str(cell).split(".")[1][1:-1])
        row_num_above = str(row_num - 1)
        row_num = str(row_num)
        sheet["A" + row_num] = current_date
        sheet["A" + row_num].number_format = "yyyy-mm-dd"
        sheet["B" + row_num] = round(float(client.futures_account()["assets"][fiat_index]["walletBalance"]), 2)
        sheet["B" + row_num].style = "Currency"
        sheet["C" + row_num] = f"=B{row_num} - B{row_num_above} - F{row_num}"
        sheet["C" + row_num].style = "Currency"
        sheet["D" + row_num] = f"=(B{row_num} - F{row_num}) / B{row_num_above} - 1"
        sheet["D" + row_num].style = "Percent"
        sheet["D" + row_num].number_format = "0.00%"
        sheet["E" + row_num] = f'=IF(ISBLANK(G{row_num}), D{row_num}, "")'
        sheet["E" + row_num].style = "Percent"
        sheet["E" + row_num].number_format = "0.00%"
        wb.save(excel_file_path)
        break

print("Done")
