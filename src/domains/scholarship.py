"""Domain B: scholarship retention (handbook 4.3.2.2, 4.4.3, 4.5, 4.11).

Contents to write:
  build_system(scholarship_type) -> (ControlSystem, list[Rule])   # rules labelled 'B1'...'B5'; cache per type
  run(cgpa, scholarship_type, credit_hours) -> (risk_score, simulation, rules)
CGPA terms are anchored at config.SCHOLARSHIP_THRESHOLDS[scholarship_type].
"""
