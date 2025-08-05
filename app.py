#Libraries
import gspread
import random
import time
import numpy as np
from collections import defaultdict
from scipy.optimize import linear_sum_assignment
from google.oauth2.service_account import Credentials

#Permissions + Sheets Setup
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)
sheet_id = "1o66pXJhxqrYNjLqngkWXBmLH_BLaJvPqaoj4Gvy6i70"
sh = client.open_by_key(sheet_id)
raw = sh.worksheet("Scoring")
del_list = sh.worksheet("DelegationList")
comm_sheet = sh.worksheet("Committee Capacity")
form = raw.get_all_values()

#Committees
TIER_1_COMMS = ["DISEC", "SOCHUM", "WHO"]

TIER_2_COMMS = ["UNHRC", "UNICEF"]

TIER_3_COMMS = ["IOGP", "PIF", "CELAC"]

TIER_4_COMMS = ["UNPFII", "EuroParl", "NATO", "IDU", "FAO"]

TIER_5_COMMS = ["UNSC", "FCC", "Cabinet", "JCC", "HCC"]

DAMN_THEY_PRO_TIER_COMMS = ["HOC", "ACC"]

class Delegation:
    def __init__(self, committee, country, score):
        self.committee = committee
        self.country = country
        self.score = int(score)

    def base_score(self, power):
        self.score **= power

    def weighing(self, amount):
        self.score *= amount

    def __repr__(self):
        return f"Delegation(country='{self.country}', committee='{self.committee}', score={self.score})"
    

delegations = []

comms = del_list.col_values(2)
pos = del_list.col_values(3)
pos_scores = del_list.col_values(4)

for i in range(len(pos)):
    committee = comms[i]
    country = pos[i]
    score = pos_scores[i]

    d = Delegation(committee, country, score)
    delegations.append(d)

for d in delegations:
    if d.committee in TIER_1_COMMS:
        d.weighing(15)
    elif d.committee in TIER_2_COMMS:
        d.weighing(18)
    elif d.committee in TIER_3_COMMS:
        d.weighing(20)
    elif d.committee in TIER_4_COMMS:
        d.weighing(25)
    elif d.committee in TIER_5_COMMS:
        d.weighing(30)
    elif d.committee in DAMN_THEY_PRO_TIER_COMMS:
        d.weighing(35)




print(delegations)