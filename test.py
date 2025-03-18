import gspread
from google.oauth2.service_account import Credentials

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)

sheet_id = "1MPxFQCkgprBk3mNUAO-ZWVZaIfobZ3Wd4wzrBSZAYEw"\

sh = client.open_by_key(sheet_id)

raw_worksheet = sh.worksheet("SGS")

value = raw_worksheet.cell(2, 1).value

print(value)