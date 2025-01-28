import gspread
from google.oauth2.service_account import Credentials

#ids




#General Variables
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)
sheet_id = "1Gj9VocX5pCg-YleZVxZ7bohpQZfr-dxtEUts06wW3cE"
sh = client.open_by_key(sheet_id)
raw_worksheet = sh.worksheet("Raw")
hcc_worksheet = sh.worksheet("HCC")
disec_worksheet = sh.worksheet("DISEC")
form = raw_worksheet.get_all_values()
disec = disec_worksheet.get_all_values()
difference = 19


for i, row in enumerate(form, start = 1):
    points = 0
    grade = raw_worksheet.cell(i + 1, 2).value
    name = raw_worksheet.cell(i + 1, 1).value

    if grade: 
        grade = int(grade) 
    
        if grade > 7 and grade < 10:
            points += 1
        elif grade >= 10:
            points += 3
        
        conferences_attended = raw_worksheet.cell(i + 1, 3).value

        if conferences_attended: 
            conferences_total = int(conferences_attended)
            if conferences_total >= 3:
                points += conferences_total * 2
        
        for awards in raw_worksheet.row_values(i + 1):
            if awards == "Best Delegate":
                points += 4
            elif awards == "Outstanding Delegate":
                points += 3
            elif awards == "Honorable Mention":
                points += 2
            elif awards == "Best Position Paper":
                points += 1        
        con_points = disec_worksheet.col_values(3)
        del con_points[0]

        print(con_points)

        ideal_con_points = con_points[min(range(len(con_points)), key = lambda i: abs(int(con_points[i]) - points))]


        cell = disec_worksheet.find(ideal_con_points)
        ideal_pos_row = cell.row
        disec_worksheet.update_cell(ideal_pos_row, 2, name)
        disec_worksheet.update_cell(ideal_pos_row, 4, "Taken")
        raw_worksheet.update_cell(i + 1, 10, points)