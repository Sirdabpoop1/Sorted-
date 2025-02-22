import gspread
from google.oauth2.service_account import Credentials

#General Variables
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)
sheet_id = "1Gj9VocX5pCg-YleZVxZ7bohpQZfr-dxtEUts06wW3cE"
sh = client.open_by_key(sheet_id)
raw_worksheet = sh.worksheet("Raw")
hcc_worksheet = sh.worksheet("HCC")
disec_worksheet = sh.worksheet("DISEC")
final_worksheet = sh.worksheet("Final")
form = raw_worksheet.get_all_values()
difference = 19

#Points
disec_points = disec_worksheet.col_values(3)
del disec_points[0]
hcc_points = hcc_worksheet.col_values(3)
del hcc_points[0]
for z in range(len(hcc_points)):
    value = hcc_points[z]
    hcc_points[z] = int(value) * 2
country_points = disec_points + hcc_points

for i, row in enumerate(form, start = 1):
    
    foundIt = False
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



        disec_taken = disec_worksheet.col_values(4)
        del disec_taken[0]
        hcc_taken = hcc_worksheet.col_values(4)
        del hcc_taken[0]
        taken_list = disec_taken + hcc_taken
        
        
        x = 0

        for x, coun_points in enumerate(country_points):
            if (taken_list[x] == "Taken"):
                country_points[x] = 10000

        ideal_coun_points = country_points[min(range(len(country_points)), key = lambda i: abs(int(country_points[i]) - points))]

        if ideal_coun_points in disec_points:
            disec_ideal_coun_points  = ideal_coun_points
            cell = disec_worksheet.find(str(disec_ideal_coun_points))
            disec_ideal_pos_row = cell.row
            disec_worksheet.update_cell(disec_ideal_pos_row, 2, name)
            disec_worksheet.update_cell(disec_ideal_pos_row, 4, "Taken")
            delegation = disec_worksheet.find(str(disec_ideal_pos_row), 1).value
        else:
            hcc_ideal_coun_points = ideal_coun_points
            hcc_ideal_coun_points = int(hcc_ideal_coun_points / 2)
            cell = hcc_worksheet.find(str(hcc_ideal_coun_points))
            hcc_ideal_pos_row = cell.row
            hcc_worksheet.update_cell(hcc_ideal_pos_row, 2, name)
            hcc_worksheet.update_cell(hcc_ideal_pos_row, 4, "Taken")
            print(hcc_ideal_pos_row)
            delegation = hcc_worksheet.find(str(hcc_ideal_pos_row), 1).value
        
        final_worksheet.update_cell(i + 1, 1, name)
        final_worksheet.update_cell(i + 1, 2, delegation)
        raw_worksheet.update_cell(i + 1, 10, points)