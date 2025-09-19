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
        self.level = None
        self.country = country
        self.committee = committee
        self.fullset = fullset
    def set_score(self):
        if self.score == 1:
            self.score = 0
            self.level = 1
        elif self.score == 2:
            self.score = 20
            self.level = 2
        else:
            self.score = 53
            self.level = 3
        if any(word in self.committee for word in CRISIS_CHECK):
            self.score += 15

    def __str__(self):
        return f"{self.country} - {self.committee} with a score of {self.score}"
    
class Delegates:
    def __init__(self, name, score, comm_prefs, pos_prefs, sheet_row):
        self.name = name
        self.score = score
        self.comm_prefs = comm_prefs
        self.pos_prefs = pos_prefs
        self.sheet_row = sheet_row
    
    def __str__(self):
        return f"I am {self.name}! I have a score of {self.score}, and want {self.pos_prefs}. I prefer {self.comm_prefs}"

class EfficiencyProMax:
    def __init__(self, assignments_data, country_data):
        self.assignments_data = assignments_data
        self.country_data = country_data
        self.delegates = []
        self.delegations = []

    def load_data(self):
        for row in self.country_data:
            score = int(row[3])
            country = row[2]
            committee = row[1]
            fullset = row[4]
            pos = Delegation(score, country, committee, fullset)
            pos.set_score()
            self.delegations.append(pos)

        self.all_delegates = []

        for i, row in enumerate(self.assignments_data[3:], start=4):
            assigned_pos = row[19].strip() if len(row) > 19 else ""

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

            if assigned_pos:
                delegation_obj = None
                assigned_pos_lower = assigned_pos.lower()
                for d in self.delegations:
                    if d.fullset.lower() == assigned_pos_lower:
                        delegation_obj = d
                        break
                if delegation_obj is None:
                    delegation_obj = Delegation(0, "", "", assigned_pos)
                    delegation_obj.set_score()

                delegate = Delegates(name, score, comm_prefs, pos_prefs, sheet_row=i)
                self.all_delegates.append((delegate, delegation_obj))

            else:
                delegate = Delegates(name, score, comm_prefs, pos_prefs, sheet_row=i)
                self.delegates.append(delegate)

    def bob_the_building_cost_matrix(self):
        num_delegates = len(self.delegates)
        num_delegations = len(self.delegations)
        BIG_M = 1e6
        ELIGIBLE_COST = 1000.0

        cost_matrix = np.full((num_delegates, num_delegations), np.inf, dtype=float)

        for d_idx, delegate in enumerate(self.delegates):
            # build preference layers
            positions = delegate.pos_prefs[:6] + [""] * max(0, 6 - len(delegate.pos_prefs))
            committees = []
            for i in range(0, 6, 2):
                if positions[i]:
                    committees.append(positions[i].split("-")[0].strip())
                else:
                    committees.append("")
            pref_order = positions[:2] + [committees[0]] + positions[2:4] + [committees[1]] + positions[4:6] + [committees[2]]

            any_eligible = False
            for g_idx, delegation in enumerate(self.delegations):
                if delegate.score < delegation.score:
                    continue

                any_eligible = True

                cost = ELIGIBLE_COST

                full = f"{delegation.committee} - {delegation.country}".strip().lower()
                committee_only = delegation.committee.strip().lower()

                matched = False
                for layer, pref in enumerate(pref_order):
                    pref_clean = str(pref).strip().lower()
                    if "-" in pref_clean and full == pref_clean:
                        cost = float(layer)
                        matched = True
                        break

                if not matched:
                    for layer, pref in enumerate(pref_order):
                        pref_clean = str(pref).strip().lower()
                        if "-" not in pref_clean and pref_clean and committee_only == pref_clean:
                            cost = float(layer) + 0.5
                            matched = True
                            break

                try:
                    score_diff = delegate.score - delegation.score
                    if delegation.score < 53:
                        cost += abs(score_diff) / 100.0
                    else:
                        cost -= delegate.score / 10.0
                except Exception:
                    pass

                cost_matrix[d_idx, g_idx] = cost

            if not any_eligible:
                cost_matrix[d_idx, :] = BIG_M

        return cost_matrix


    def assign_time(self):
        cost_matrix = self.bob_the_building_cost_matrix()
        BIG_M = 1e6

        # Stage 1: Mask infeasible
        feasible_matrix = cost_matrix.copy()
        for i, delegate in enumerate(self.delegates):
            for j, delegation in enumerate(self.delegations):
                if delegate.score < delegation.score:
                    feasible_matrix[i, j] = BIG_M
        
        row_ind, col_ind = linear_sum_assignment(feasible_matrix)
        
        assignments = []
        assigned_delegates = set()
        assigned_delegations = set()

        for r, c in zip(row_ind, col_ind):
            if feasible_matrix[r, c] < BIG_M:
                assignments.append((self.delegates[r], self.delegations[c]))
                assigned_delegates.add(r)
                assigned_delegations.add(c)

        # Stage 2: Greedy Fallback
        for i, delegate in enumerate(self.delegates):
            if i in assigned_delegates:
                continue

            available = [j for j in range(len(self.delegations)) if j not in assigned_delegations]

            if available:
                best = min(available, key=lambda j: self.delegations[j].score)
                assignments.append((delegate, self.delegations[best]))
                assigned_delegations.add(best)
            else:
                dummy = Delegation(0, "UNASSIGNED", "", "UNASSIGNED")
                assignments.append((delegate, dummy))

        return assignments + self.all_delegates

    def pinging_pinger_that_pings(self, assignments_result, ping_col="U"):
        assignments_sheet = sh.worksheet("Assignments")
        ping_updates = []

        for delegate, delegation in assignments_result:
            if delegation in ("UNASSIGNED", "CANCELLED"):
                continue

            reason = None

            if delegation.level == 3:
                reason = "Ping (Level 3 position)"

            elif abs(delegate.score - delegation.score) > 15:
                reason = f"Ping (Score mismatch: {delegate.score} vs {delegation.score})"

            if reason:
                ping_updates.append({
                    "range": f"{ping_col}{delegate.sheet_row}",
                    "values": [[reason]]
                })
                print(f"DEBUG: Pinging {delegate.name} ({delegate.score}) "
                    f"-> {delegation.fullset} ({delegation.score}) "
                    f"Reason: {reason}")

        requests = []
        for row, reason in ping_updates:
            requests.append({
                "range": f"{ping_col}{row}",
                "values": [[reason]]
            })
        try:
            safe_update(assignments_sheet.batch_update, requests)
            print(f"Ping column {ping_col} updated for {len(requests)} rows.")
        except Exception as e:
            print("Failed to write pings:", e)


    def writing_to_sheet(self, assignments, start_row=4, col="T"):
        assignments_sorted = sorted(assignments, key=lambda x: x[0].sheet_row)
        values = [[assignment[1].fullset] for assignment in assignments_sorted]
        start_row = assignments_sorted[0][0].sheet_row if assignments_sorted else 4
        cell_range = f"{col}{start_row}:{col}{start_row + len(values) - 1}"
        safe_update(assignments_sheet.update, values, cell_range)
        print(f"Assignments written to column {col} starting at row {start_row}")

    def debug_print(self):
        print("\n=== Delegates ===")
        for d in self.delegates:
            print(d)

optimizer = EfficiencyProMax(assignments_data, raw_countries)
optimizer.load_data()
assignments_result = optimizer.assign_time()
optimizer.writing_to_sheet(assignments_result, start_row=4, col="T")
optimizer.pinging_pinger_that_pings(assignments_result)
print("That's all folks!")