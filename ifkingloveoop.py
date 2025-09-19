# Libraries
import gspread
import time
import numpy as np
from collections import defaultdict
from scipy.optimize import linear_sum_assignment
from google.oauth2.service_account import Credentials

# Permissions + Sheets Setup
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)
sheet_id = "13pB32e0QvE0QlGSnjtIDD6hF04N715RV0l_rvM1PnlY"
sh = client.open_by_key(sheet_id)
assignments_sheet = sh.worksheet("Assignments")
del_list = sh.worksheet("DelegationList")
assignments_data = assignments_sheet.get_all_values()
raw_countries = del_list.get_all_values()

CRISIS_CHECK = ["CC", "HOC", "UNSC", "Cabinet"]

# Ensures that the program continues running, even after hitting API quotas
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

# Classes
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
        self.all_delegates = []

    def load_previous_assignments(self):
        self.all_delegates = []
        assigned_delegation_names = set()

        for i, row in enumerate(self.assignments_data[3:], start=4):
            name = row[0].strip()
            assigned_pos = row[19].strip() if len(row) > 19 else ""

            if not name:
                continue

            # Find delegate object in sheet
            delegate_obj = next((d for d in self.all_delegates_from_sheet if d.name.lower() == name.lower() and d.sheet_row == i), None)
            if not delegate_obj:
                continue

            if assigned_pos and assigned_pos.upper() != "UNASSIGNED":
                # Treat whatever is in the sheet as fixed assignment
                delegation_obj = Delegation(0, "", "", assigned_pos)
                self.all_delegates.append((delegate_obj, delegation_obj))
                assigned_delegation_names.add(assigned_pos.lower())

        # Build list of delegations still available for assignment
        self.available_delegations = [
            d for d in self.delegations
            if d.fullset.lower() not in assigned_delegation_names
        ]
        print(f"DEBUG: {len(self.available_delegations)} delegations available after fixed assignments.")





    def load_data(self):
        # Load all delegations first
        self.delegations = []
        for row in self.country_data:
            if len(row) < 5:
                continue
            try:
                score = int(row[3]) if row[3].strip() else 0
                country = row[2].strip()
                committee = row[1].strip()
                fullset = row[4].strip()
                pos = Delegation(score, country, committee, fullset)
                pos.set_score()
                self.delegations.append(pos)
            except (ValueError, IndexError) as e:
                print(f"Warning: Skipping invalid delegation row: {row} - {e}")

        # Load ALL delegates (both assigned and unassigned)
        self.all_delegates_from_sheet = []  # Store all delegates for reference
        self.delegates = []  # Only unassigned delegates for new assignment
        
        for i, row in enumerate(self.assignments_data[3:], start=4):
            if len(row) < 20:
                continue
                
            name = row[0].strip()
            if not name:
                continue
            
            assigned_pos = row[19].strip() if len(row) > 19 else ""
            score = int(row[3]) if row[3].strip().isdigit() else 0
            
            comm_prefs = []
            pos_prefs = []
            for col in range(5, 17, 2):
                if col < len(row):
                    cell = str(row[col]).strip()
                    if cell:
                        pos_prefs.append(cell)
                        comm = cell.split("-")[0].strip()
                        if comm not in comm_prefs:
                            comm_prefs.append(comm)

            delegate = Delegates(name, score, comm_prefs, pos_prefs, sheet_row=i)
            self.all_delegates_from_sheet.append(delegate)
            
            # Only add to delegates list if not assigned
            if not assigned_pos or assigned_pos == "UNASSIGNED":
                self.delegates.append(delegate)

    def bob_the_building_cost_matrix(self, delegates=None, delegations=None):
        if delegates is None:
            delegates = self.delegates
        if delegations is None:
            delegations = self.delegations

        num_delegates = len(delegates)
        num_delegations = len(delegations)
        BIG_M = 1e6
        ELIGIBLE_COST = 1000.0

        cost_matrix = np.full((num_delegates, num_delegations), np.inf, dtype=float)

        for d_idx, delegate in enumerate(delegates):
            positions = delegate.pos_prefs[:6] + [""] * max(0, 6 - len(delegate.pos_prefs))
            committees = [positions[i].split("-")[0].strip() if positions[i] else "" for i in range(0,6,2)]
            pref_order = positions[:2] + [committees[0]] + positions[2:4] + [committees[1]] + positions[4:6] + [committees[2]]

            for g_idx, delegation in enumerate(delegations):
                if delegate.score < delegation.score:
                    cost_matrix[d_idx, g_idx] = BIG_M
                    continue

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

                score_diff = delegate.score - delegation.score
                if delegation.score < 53:
                    cost += abs(score_diff)/100.0
                else:
                    cost -= delegate.score / 10.0

                cost_matrix[d_idx, g_idx] = cost

        return cost_matrix

    def assign_time(self):
        print("="*60)
        print("ASSIGNMENT PROCESS STARTED")
        print(f"Delegates to assign: {len(self.delegates)}")
        print(f"Fixed assignments: {len(self.all_delegates)}")

        if not self.delegates:
            print("No new delegates to assign")
            return self.all_delegates

        # Build cost matrix for unassigned delegates
        cost_matrix = self.bob_the_building_cost_matrix(self.delegates, self.available_delegations)
        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        new_assignments = []

        for r, c in zip(row_ind, col_ind):
            if cost_matrix[r, c] >= 1e6:
                # Skip incompatible matches
                continue

            delegate_obj = self.delegates[r]
            delegation_obj = self.available_delegations[c]

            # Ensure every delegation has a valid fullset
            if not getattr(delegation_obj, "fullset", "").strip():
                delegation_obj.fullset = f"UNASSIGNED PLACEHOLDER {delegation_obj.committee} - {delegation_obj.country}"

            new_assignments.append((delegate_obj, delegation_obj))
            print(f"DEBUG: Assigned {delegate_obj.name} -> {delegation_obj.fullset}")

        # Handle any remaining unassigned delegates (greedy fallback)
        assigned_indices = set(row_ind)
        for i, delegate_obj in enumerate(self.delegates):
            if i in assigned_indices:
                continue
            if self.available_delegations:
                # Pick the first remaining delegation
                delegation_obj = self.available_delegations.pop(0)
                if not getattr(delegation_obj, "fullset", "").strip():
                    delegation_obj.fullset = f"UNASSIGNED PLACEHOLDER {delegation_obj.committee} - {delegation_obj.country}"
                new_assignments.append((delegate_obj, delegation_obj))
                print(f"DEBUG: Fallback assignment: {delegate_obj.name} -> {delegation_obj.fullset}")
            else:
                new_assignments.append((delegate_obj, "UNASSIGNED"))
                print(f"DEBUG: No positions left: {delegate_obj.name} -> UNASSIGNED")

        # Combine with existing fixed assignments
        all_assignments = self.all_delegates + new_assignments
        print(f"DEBUG: Total assignments: {len(all_assignments)}")
        return all_assignments



    def writing_to_sheet(self, assignments, col="T"):
        updates = []

        for delegate, delegation in assignments:
            # Skip blank delegate names
            if not delegate.name.strip():
                continue

            # Decide value to write
            if isinstance(delegation, str):
                value_to_write = delegation
            else:
                value_to_write = delegation.fullset.strip() if delegation.fullset.strip() else "UNASSIGNED"
            
            updates.append({
                "range": f"{col}{delegate.sheet_row}",
                "values": [[value_to_write]]
            })

        if updates:
            try:
                safe_update(assignments_sheet.batch_update, updates)
                print(f"Wrote {len(updates)} new assignments to column {col}.")
            except Exception as e:
                print("❌ Failed to write assignments:", e)
        else:
            print("No new assignments to write.")

    def pinging_pinger_that_pings(self, assignments_result, ping_col="U"):
        assignments_sheet = sh.worksheet("Assignments")
        ping_updates = []

        for delegate, delegation in assignments_result:
            if (delegate, delegation) in self.all_delegates:
                continue

            if not delegate.name.strip():
                continue

            if delegation in ("UNASSIGNED", "CANCELLED"):
                continue

            reason = None

            if hasattr(delegation, 'level') and delegation.level == 3:
                reason = "Ping (Level 3 position)"

            elif hasattr(delegation, 'score') and abs(delegate.score - delegation.score) > 30:
                reason = f"Ping (Score mismatch: {delegate.score} vs {delegation.score})"

            if reason:
                ping_updates.append({
                    "range": f"{ping_col}{delegate.sheet_row}",
                    "values": [[reason]]
                })
                print(f"DEBUG: Pinging {delegate.name} ({delegate.score}) "
                    f"-> {delegation.fullset if hasattr(delegation, 'fullset') else delegation} ({delegation.score if hasattr(delegation, 'score') else 'N/A'}) "
                    f"Reason: {reason}")

        if ping_updates:
            try:
                safe_update(assignments_sheet.batch_update, [{"range": u["range"], "values": u["values"]} for u in ping_updates])
                print(f"Ping column {ping_col} updated for {len(ping_updates)} rows.")
            except Exception as e:
                print("Failed to write pings:", e)

# Main execution
optimizer = EfficiencyProMax(assignments_data, raw_countries)
optimizer.load_data()                      # Loads all delegates and delegations
optimizer.load_previous_assignments()      # Sets fixed assignments & self.available_delegations
assignments_result = optimizer.assign_time()  # Perform assignment
optimizer.writing_to_sheet(assignments_result, col="T")  # Write to sheet
optimizer.pinging_pinger_that_pings(assignments_result, ping_col="U")  # Update ping column

print("That's all folks!")
