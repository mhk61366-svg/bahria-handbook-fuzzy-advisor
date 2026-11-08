"""Build scikit-fuzzy variables and membership functions (see DESIGN.md section 5).

Contents to write:
  cgpa_antecedent(threshold: float) -> Antecedent
      terms anchored at threshold T, w = config.GRADE_STEP, w_up = min(w, 4.00 - T):
        below_min  trapmf [0, 0, T-w, T]
        borderline trimf  [T-w, T, T+w_up]
        safe       trapmf [T, T+w_up, 4.00, 4.00]
      (w_up truncation guarantees CGPA 4.00 is fully 'safe' even for T = 3.75)
  credit_load_antecedent() -> Antecedent       # under_load / regular, anchored at 9 and 18, step 3
  probation_count_antecedent() -> Antecedent   # none / first / second (narrow triangles on 0,1,2)
  risk_consequent() -> Consequent              # low / moderate / high / critical on [0, 100]
"""
