import gspread
from google.oauth2.service_account import Credentials

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)
sheet_id = "1Gj9VocX5pCg-YleZVxZ7bohpQZfr-dxtEUts06wW3cE"
sh = client.open_by_key(sheet_id)
raw_worksheet = sh.worksheet("Raw")
rows = raw_worksheet.get_all_values()

for i, row in enumerate(rows, start = 1):
    points = 0
    grade = raw_worksheet.cell(i + 1, 2).value
    conferences_attended = raw_worksheet.cell(i + 1, 3).value
    if grade:
        grade = int(grade)
        if grade > 7 and grade < 10:
            points += 1
        elif grade >= 10:
            points += 2
    if conferences_attended:
        conferences_total = int(conferences_attended)
        if conferences_total >= 3:
            points += conferences_total * 2
    if grade:
        print(grade)
        print(conferences_total)
        print(points)
        raw_worksheet.update_cell(i + 1, 10, points)