#Libraries
import gspread
import time
import numpy as np
from collections import defaultdict
from scipy.optimize import linear_sum_assignment
from google.oauth2.service_account import Credentials

#Permissions + Sheets Setup
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)
sheet_id = "1Q0rmXKE6p9C0TZgQfaGgVrXiKFZtVO56mZtNvCn0oYc"
sh = client.open_by_key(sheet_id)
assignments_sheet = sh.worksheet("Assignments")
del_list = sh.worksheet("DelegationList")
assignments_data = assignments_sheet.get_all_values()
raw_countries = del_list.get_all_values()

#General Variables
CRISIS_CHECK = ["CC", "HOC", "UNSC", "Cabinet"]

#Ensures that the program continues running, even after hitting API quotas

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

#Classes

class Delegation:
    def __init__(self, score, country, committee, fullset):
        self.score = score
        self.country = country
        self.committee = committee
        self.fullset = fullset
    def set_score(self):
        if self.score == 1:
            self.score = 0
        elif self.score == 2:
            self.score = 20
        else:
            self.score = 53
        if any(word in self.committee for word in CRISIS_CHECK):
            self.score += 15

    def __str__(self):
        return f"{self.country} - {self.committee} with a score of {self.score}"
    
class Delegates:
    def __init__(self, name, score, comm_prefs, pos_prefs):
        self.name = name
        self.score = score
        self.comm_prefs = comm_prefs
        self.pos_prefs = pos_prefs
    
    def __str__(self):
        return f"I am {self.name}! I have a score of {self.score}, and want {self.pos_prefs}. I prefer {self.comm_prefs}"

class EfficiencyProMax:
    def __init__(self, assignments_data, country_data):
        self.assignments_data = assignments_data
        self.assignments_data = country_data
        self.delegates = []
        self.delegations = []
        self.BIG_M = 10,000
    
    def load_data(self):
        for i, row in enumerate(raw_countries, start = 1):
            score = int(row[3])
            country = row[2]
            committee = row[1]
            fullset = row[4]
            pos = Delegation(score, country, committee, fullset)
            pos.set_score()
            self.delegations.append(pos)

        for i,  row in enumerate(assignments_data[3:], start = 4):
            name = row[0]
            score = int(row[3])
            comm_prefs = []
            pos_prefs = []
            for col in range(5, 17, 2):
                cell = str(row[col]).strip()
                if cell:
                    pos_prefs.append(row[col])
                    comm = row[col].split("-")[0].strip()
                    if comm not in comm_prefs:
                        comm_prefs.append(comm)
            dels = Delegates(name, score, comm_prefs, pos_prefs)
            self.delegates.append(dels)
                
    def bob_the_building_cost_matrix(self):
        num_delegates = len(self.delegates)
        num_delegations = len(self.delegations)
        cost_matrix = np.full((num_delegates, num_delegations), 9999, dtype=float)
        
        for i, delegate in enumerate(self.delegates):
            for j, delegation in enumerate(self.delegations):
                if delegate.score < delegation.score:
                    continue
                    
                try:
                    pref_rank = delegate.comm_prefs.index(delegation.committee) + 1
                except ValueError:
                    pref_rank = len(delegate.comm_prefs) + 1

                max_pref = len(delegate.comm_prefs)
                if max_pref == 0:
                    pref_score = 0
                else:
                    pref_score = (max_pref - (pref_rank - 1)) / max_pref

                score_fit = min(delegate.score / 200, 1.0) 

                match_score = (0.9 * pref_score) + (0.1 * score_fit)

                cost_matrix[i, j] = 1 - match_score
        
        return cost_matrix
    
    def assign_time(self):
        cost_matrix = self.bob_the_building_cost_matrix()
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        assignments = []
        for r, c in zip(row_ind, col_ind):
            if cost_matrix[r, c] < 9999:
                assignments.append((self.delegates[r], self.delegations[c]))
        return assignments
    
    def writing_to_sheet(self, assignments, start_row=4, col="T"):
        values = [[d[1].fullset] for d in assignments]
        cell_range = f"{col}{start_row}:{col}{start_row + len(values) - 1}"
        safe_update(assignments_sheet.update, cell_range, values)
        print(f"Assignments written to column {col} starting at row {start_row}")

    def debug_print(self):
        print("\n=== Delegates ===")
        for d in self.delegates:
            print(d)

optimizer = EfficiencyProMax(assignments_data, raw_countries)
optimizer.load_data()
assignments_result = optimizer.assign_time()
optimizer.writing_to_sheet(assignments_result, start_row=4, col="T")
print("That's all folks!")