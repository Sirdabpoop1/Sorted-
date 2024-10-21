'''
import gspread
import django
from google.oauth2.service_account import Credentials



def index(request):
    if request.method == "POST":
        gsheet_id = request.POST.gen("gsheet_id")
        print(gsheet_id)

scopes = [
    "https://www.googleapis.com/auth/spreadsheets"
]

creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)

sheets_id = "1Gj9VocX5pCg-YleZVxZ7bohpQZfr-dxtEUts06wW3cE"
sheet = client.open_by_key(sheets_id)

values_list = sheet.sheet1.row_values(2)

print(values_list)
'''