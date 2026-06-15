"""
generate_sample.py - Small, realistic LendingClub sample using the REAL schema.

This produces a tiny stand-in dataset with the SAME column names and formats as
the public LendingClub files, so the credit operating model can be built and
verified now. Replace these files with the real Kaggle CSVs (drop them in this
folder, same names without `_sample`) and everything points at real data.

Real files this mirrors:
  - accepted_2007_to_2018Q4.csv   -> accepted_sample.csv
  - rejected_2007_to_2018Q4.csv   -> rejected_sample.csv

Deterministic (seeded) so the sample is reproducible. Run: python generate_sample.py
"""

import csv
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(42)

# Grade -> (interest-rate band, probability a matured loan charged off). Risk and
# price both rise down the grades, the way LendingClub actually priced them.
GRADES = {
    "A": (0.0650, 0.06), "B": (0.1050, 0.10), "C": (0.1400, 0.16),
    "D": (0.1800, 0.22), "E": (0.2200, 0.29), "F": (0.2600, 0.36), "G": (0.2950, 0.43),
}
GRADE_W = {"A": 18, "B": 26, "C": 24, "D": 16, "E": 10, "F": 4, "G": 2}  # mix
TERMS = [36, 60]
PURPOSES = ["debt_consolidation", "credit_card", "home_improvement", "major_purchase",
            "small_business", "medical", "car", "other"]
HOME = ["RENT", "MORTGAGE", "OWN"]
VERIF = ["Verified", "Source Verified", "Not Verified"]
STATES = ["CA", "TX", "NY", "FL", "IL", "NJ", "PA", "OH", "GA", "NC", "VA", "WA"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
EMP = ["< 1 year", "1 year", "2 years", "3 years", "5 years", "7 years", "10+ years"]


def _installment(principal, annual_rate, months):
    r = annual_rate / 12.0
    return principal * r / (1 - (1 + r) ** -months) if r else principal / months


def _pick_grade():
    grades, weights = zip(*GRADE_W.items())
    return random.choices(grades, weights=weights)[0]


def build_accepted(n=140):
    rows = []
    for i in range(n):
        g = _pick_grade()
        base_rate, pd = GRADES[g]
        rate = round(base_rate + random.uniform(-0.012, 0.012), 4)
        sub = f"{g}{random.randint(1, 5)}"
        term = random.choice(TERMS)
        amt = random.choice([5000, 8000, 10000, 12000, 15000, 20000, 24000, 30000, 35000, 40000])
        funded = amt
        inst = round(_installment(funded, rate, term), 2)
        year = random.choice([2015, 2015, 2016, 2016, 2017, 2017, 2018])
        month = random.choice(MONTHS)
        fico_low = random.choice([660, 675, 690, 700, 710, 720, 740, 760, 780])
        income = random.choice([45000, 55000, 62000, 70000, 85000, 95000, 110000, 130000])

        # Status: a slice are still on book (Current/Late); the rest matured to
        # Fully Paid or Charged Off, with charge-off odds driven by grade.
        roll = random.random()
        if roll < 0.18:
            status = "Current"
        elif roll < 0.23:
            status = "Late (31-120 days)"
        else:
            status = "Charged Off" if random.random() < pd else "Fully Paid"

        full_int = inst * term - funded
        if status == "Fully Paid":
            rec_prncp, rec_int, recov = funded, round(full_int, 2), 0.0
        elif status == "Charged Off":
            f = random.uniform(0.20, 0.70)
            rec_prncp = round(funded * f, 2)
            rec_int = round(full_int * f * 0.6, 2)
            recov = round((funded - rec_prncp) * random.uniform(0.0, 0.15), 2)
        elif status == "Current":
            f = random.uniform(0.25, 0.75)
            rec_prncp, rec_int, recov = round(funded * f, 2), round(full_int * f, 2), 0.0
        else:  # Late
            f = random.uniform(0.15, 0.55)
            rec_prncp, rec_int, recov = round(funded * f, 2), round(full_int * f * 0.8, 2), 0.0
        total_pymnt = round(rec_prncp + rec_int + recov, 2)

        rows.append({
            "id": 100000 + i,
            "loan_amnt": amt, "funded_amnt": funded,
            "term": f" {term} months", "int_rate": f"{rate * 100:.2f}%",
            "installment": inst, "grade": g, "sub_grade": sub,
            "emp_length": random.choice(EMP), "home_ownership": random.choice(HOME),
            "annual_inc": income, "verification_status": random.choice(VERIF),
            "issue_d": f"{month}-{year}", "loan_status": status,
            "purpose": random.choice(PURPOSES), "dti": round(random.uniform(5, 35), 2),
            "fico_range_low": fico_low, "fico_range_high": fico_low + 4,
            "addr_state": random.choice(STATES),
            "total_pymnt": total_pymnt, "total_rec_prncp": rec_prncp,
            "total_rec_int": rec_int, "recoveries": recov,
            "last_pymnt_d": f"{random.choice(MONTHS)}-{year + 1}",
        })
    return rows


def build_rejected(n=70):
    rows = []
    for i in range(n):
        year = random.choice([2015, 2016, 2017, 2018])
        rows.append({
            "Amount Requested": random.choice([3000, 5000, 8000, 12000, 18000, 25000, 35000]),
            "Application Date": f"{year}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            "Loan Title": random.choice(["debt_consolidation", "credit_card_refinancing",
                                         "business", "other"]),
            "Risk_Score": random.choice(["", 580, 600, 620, 640, 660]),
            "Debt-To-Income Ratio": f"{random.uniform(15, 55):.1f}%",
            "Zip Code": f"{random.randint(1, 999):03d}xx",
            "State": random.choice(STATES),
            "Employment Length": random.choice(EMP + ["< 1 year"]),
            "Policy Code": 0,
        })
    return rows


def _write(name, rows):
    path = os.path.join(HERE, name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {name}: {len(rows)} rows")


if __name__ == "__main__":
    _write("accepted_sample.csv", build_accepted())
    _write("rejected_sample.csv", build_rejected())
    print("done. Replace with the real Kaggle CSVs to run on real data.")
