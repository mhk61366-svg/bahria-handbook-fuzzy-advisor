"""Handbook-derived constants and tunable design parameters. NO logic here.

Page numbers are PRINTED page numbers; PDF page = printed + 10.
Every handbook number carries its clause. Design assumptions are marked ASSUMPTION
and must also appear in DESIGN.md section 12.
"""

# --- CGPA scale -------------------------------------------------------------
CGPA_MIN, CGPA_MAX = 0.0, 4.0        # grade points 0.00-4.00, section 5.3.1, p.70
GRADE_STEP = 0.33                    # ASSUMPTION A3: adjacent grade points differ by ~0.33 (5.3.1, p.70);
                                     # used as the fuzzy transition half-width around every threshold

# --- Domain A: probation and drop (section 5.5, p.71-72) -------------------
PROBATION_MIN_CGPA = 2.0             # 5.5.1, p.71 (BBA/BEE/BS programmes)
DROP_AFTER_PROBATIONS = 2            # 5.5.3, p.71: drop after failing again following two consecutive probations
PROBATION_COUNTS = (0, 1, 2)         # consecutive probations already recorded before this semester's result

# --- Domain B: scholarship retention ----------------------------------------
# Non-engineering programmes only (ASSUMPTION A2).
SCHOLARSHIP_THRESHOLDS = {
    "merit_batch_topper": 3.75,          # 4.4.3.3, p.52 (3.60 applies to engineering - out of scope)
    "advance_merit_continuation": 3.50,  # 4.3.2.2 p.50; 4.3.3.1.2(b) p.50-51
    "financial_assistance": 2.50,        # 4.5.2 and 4.5.3(d), p.53
}
SCHOLARSHIP_LABELS = {
    "merit_batch_topper": "Merit scholarship (batch topper)",
    "advance_merit_continuation": "Advance merit scholarship (continuation)",
    "financial_assistance": "Financial assistance scholarship (FAS)",
}

# --- Credit load (used as an input to Domain B) ------------------------------
CREDITS_MIN = 9                      # 1.10.1, p.8 (except final semester)
CREDITS_MAX = 18                     # 1.10.2.1, p.8 (non-engineering; final-semester extra course out of scope)
CREDIT_STEP = 3                      # ASSUMPTION A1: one 3-credit course = fuzzy transition half-width
                                     # "regular course load" (4.4.3.5, 4.12(b)) is NOT defined numerically in the handbook

# --- Output variable ---------------------------------------------------------
RISK_UNIVERSE = (0, 100)
RISK_TERMS = ("low", "moderate", "high", "critical")   # ordered by severity

# --- Numerical resolution ----------------------------------------------------
CGPA_RESOLUTION = 0.01
CREDIT_RESOLUTION = 0.5
RISK_RESOLUTION = 1

# --- Highlight colours, one per rule (traceability.csv colour_hex) ------------
RULE_COLORS = [
    "#FFEB3B", "#80DEEA", "#A5D6A7", "#F48FB1", "#FFCC80", "#CE93D8",
    "#B0BEC5", "#E6EE9C", "#90CAF9", "#FFAB91", "#C5E1A5", "#BCAAA4",
]
