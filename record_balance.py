from binance.client import Client
from credentials import API_KEY, API_SECRET
from openpyxl import load_workbook
import re
from datetime import date

client = Client(API_KEY, API_SECRET)
current_date = date.today().isoformat()
wb = load_workbook('Trade Record.xlsx')
sheet = wb["Balance Record"]
for cell in sheet["A"]:
    if cell.value == None:
        row_num = int(re.findall(r"\d+", str(cell))[0])
        row_num_above = str(row_num - 1)
        row_num = str(row_num)
        sheet["A" + row_num] = current_date
        sheet["A" + row_num].number_format = "yyyy-mm-dd"
        sheet["B" + row_num] = round(float(client.futures_account()["totalWalletBalance"]), 2)
        sheet["B" + row_num].style = "Currency"
        sheet["C" + row_num] = f"=B{row_num} - B{row_num_above} - E{row_num}"
        sheet["C" + row_num].style = "Currency"
        sheet["D" + row_num] = f"=(B{row_num} - E{row_num}) / B{row_num_above} - 1"
        sheet["D" + row_num].style = "Percent"
        sheet["D" + row_num].number_format = "0.00%"
        wb.save('Trade Record.xlsx')
        break

print("Done")
