#Libraries
import gspread
from google.oauth2.service_account import Credentials
import random
import time

#General Variables
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)
sheet_id = "1Gj9VocX5pCg-YleZVxZ7bohpQZfr-dxtEUts06wW3cE"
sh = client.open_by_key(sheet_id)
raw_worksheet = sh.worksheet("Raw")
disec_worksheet = sh.worksheet("DISEC")
las_worksheet = sh.worksheet("LAS")
acc_worksheet = sh.worksheet("ACC")
final_worksheet = sh.worksheet("Final")
form = raw_worksheet.get_all_values()

#Sets a list per committee with point values. Each row has a preset point value, which correlates to a country.
disec_points = disec_worksheet.col_values(2)
del disec_points[0]
las_points = las_worksheet.col_values(2)
del las_points[0]
for z in range(len(las_points)):
    value = las_points[z]
    las_points[z] = int(value) * 2
acc_points = acc_worksheet.col_values(2)
del acc_points[0]
for p in range(len(acc_points)):
    value = acc_points[p]
    acc_points[p] = int(value) * 3

country_points = disec_points + las_points + acc_points

#Ensures that, when the quota for updates is met, the program will pause until the quota is reset, before continuing to run.

def safe_update(func, *args, **kwargs):
    max_retries = 5
    retries = 0
    while retries < max_retries:
        try:
            return func(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            print(f"APIError: {e}")
            if "Quota exceeded" in str(e):
                print(f"Quota exceeded while updating. Now waiting! This is attempt {retries + 1}/{max_retries}")
                time.sleep(60)
                retries += 1
            else:
                print(f"Error: {str(e)}. Exiting the program.")
                raise e
    
    print("Quota still exceeded after multiple retries when updating")
    return None

#Ensures that, when the quota for reading is met, the program will pause until the quota is reset, before continuing to run.

def safe_read(func, *args, **kwargs):
    max_retries = 5
    retries = 0
    while retries < max_retries:
        try:
            return func(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            print(f"APIError: {e}")
            if "Quota exceeded" in str(e):
                print(f"Quota exceeded while reading. Now waiting! This is attempt {retries + 1}/{max_retries}")
                time.sleep(60)
                retries += 1
            else:
                print(f"Error: {str(e)}. Exiting the program.")
                raise e
    
    print("Quota still exceeded after multiple retries when reading")
    return None

#Core of the program begins here!

#Iterates through each delegate dynamically, based on the number of rows in the GSheet.
for i, row in enumerate(form, start = 1):
    points = 0
    grade = safe_read(raw_worksheet.cell, i + 1, 4).value

    #Prevents gaps in the sheet from breaking the program.
    if grade:
        name = safe_read(raw_worksheet.cell, i + 1, 2).value
        done = safe_read(final_worksheet.find, name)
    #Prevents delegates who registered twice from being given two assignments
    if grade and not done:
        grade = int(grade)
    
        #Adding points based on grade
        if grade == 8:
            points += 0.4
        elif grade == 9:
            points += 0.8
        elif grade == 10:
            points += 1.2
        elif grade == 11:
            points += 1.6
        elif grade == 12:
            points += 2
        
        #Adding points based on conferences attended
        conferences_attended = safe_read(raw_worksheet.cell, i + 1, 5).value

        if conferences_attended: 
            conferences_total = int(conferences_attended)
            if conferences_total >= 3:
                points += conferences_total * 0.75
        
        #Adding points based on awards
        for awards in safe_read(raw_worksheet.row_values, i + 1):
            if awards == "Best Delegate":
                points += 2.3
            elif awards == "Outstanding Delegate":
                points += 1.8
            elif awards == "Honorable Mention":
                points += 1.2
            elif awards == "Best Position Paper":
                points += 0.6


        #Creating a "Taken" list for each committee. Each item is either a space or the word "Taken"
        disec_taken = safe_read(disec_worksheet.col_values, 4)
        del disec_taken[0]
        las_taken = safe_read(las_worksheet.col_values, 4)
        del las_taken[0]
        acc_taken = safe_read(acc_worksheet.col_values, 4)
        del acc_taken[0]
        taken_list = disec_taken + las_taken + acc_taken
        
        #Compares the "Taken" list to the list of country points. Sets every country_point item that shares the same index as a "Taken" item to an
        #absurd number that will never be the closest. As a result, it essentially removes that country as a possible option for a delegate to take.

        x = 0
        for x, point in enumerate(disec_points):
            if disec_taken[x] == "Taken":
                disec_points[x] = 100000000
        for x, point in enumerate(las_points):
            if las_taken[x] == "Taken":
                las_points[x] = 100000000
        for x, point in enumerate(acc_points):
            if acc_taken[x] == "Taken":
                acc_points[x] = 100000000
        
        country_points = disec_points + las_points + acc_points

        #Gets the delegate's preferences
        com_preference = [safe_read(raw_worksheet.cell, i + 1, col).value for col in [15, 17]]
        del_preference = [safe_read(raw_worksheet.cell, i + 1, col).value for col in [16, 18]]


        #Checks to see if the delegate's points is somewhat close to the position that they prefer (changeable). If it is, then it sets them as that position, instead
        #of the one with the closest amount of points.
        a = 0
        ideal_coun_points = 0
        prefered = False

        for choice in com_preference:
            if prefered == True:
                break
            elif choice == "LAS":
                prefered_cell = safe_read(las_worksheet.find, del_preference[a])
                las_prefered_point = safe_read(las_worksheet.cell, prefered_cell.row, 2)
                prefered_del_points = int(las_prefered_point.value) * 2
                if abs(int(prefered_del_points) - points) <= 0.5:
                    ideal_coun_points = prefered_del_points
                    prefered = True
            elif choice == "DISEC":
                prefered_cell = safe_read(disec_worksheet.find, del_preference[a])
                prefered_del_points = safe_read(disec_worksheet.cell, prefered_cell.row, 2)
                if abs(int(prefered_del_points.value) - points) <= 0.5:
                    ideal_coun_points = prefered_del_points.value
                    prefered = True
            elif choice == "ACC":
                prefered_cell = safe_read(acc_worksheet.find, del_preference[a])
                acc_prefered_point = safe_read(acc_worksheet.cell, prefered_cell.row, 2)
                prefered_del_points = int(acc_prefered_point.value) * 3
                if abs(int(prefered_del_points) - points) <= 0.5:
                    ideal_coun_points = prefered_del_points
                    prefered = True
            a += 1
        
        if ideal_coun_points == 0:
            ideal_coun_points = country_points[min(range(len(country_points)), key = lambda i: abs(int(country_points[i]) - points))]
            
        y = 0
        #Prints to the Google Sheet that the recently assigned position is now taken.
        if ideal_coun_points in disec_points:
            for val in disec_points:
                if str(ideal_coun_points) == str(val):
                    good_row = y + 2
                y += 1
            safe_update(disec_worksheet.update_cell, good_row, 3, name)
            safe_update(disec_worksheet.update_cell, good_row, 4, "Taken")
            delegation = safe_read(disec_worksheet.cell, good_row, 1)
            delegation = delegation.value
        elif ideal_coun_points in las_points:
            for val in las_points:
                if str(ideal_coun_points) == str(val):
                    good_row = y + 2
                y += 1
            safe_update(las_worksheet.update_cell, good_row, 3, name)
            safe_update(las_worksheet.update_cell, good_row, 4, "Taken")
            delegation = safe_read(las_worksheet.cell, good_row, 1)
            delegation = delegation.value
        elif ideal_coun_points in acc_points:
            for val in acc_points:
                if str(ideal_coun_points) == str(val):
                    good_row = y + 2
                y += 1
            safe_update(acc_worksheet.update_cell, good_row, 3, name)
            safe_update(acc_worksheet.update_cell, good_row, 4, "Taken")
            delegation = safe_read(acc_worksheet.cell, good_row, 1)
            delegation = delegation.value
        
        #Updates the final worksheet with the delegate's name and position
        safe_update(final_worksheet.update_cell, i + 1, 1, name)
        safe_update(final_worksheet.update_cell, i + 1, 2, delegation)
        
        #Updates the delegate's points by printing their points directly to the Google Sheet.
        result = safe_update(raw_worksheet.update_cell, i + 1, 19, points)

        if result is not None:
            print(f"Completed {name}'s assignment with {points} points!")
        else:
            print(f"Failed to update {name}'s assignment after multiple retries.")
        time.sleep(random.uniform(1, 3))