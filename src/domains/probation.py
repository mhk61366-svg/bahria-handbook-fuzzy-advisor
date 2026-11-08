"""Domain A: probation and drop (handbook 5.5, p.71-72).

Contents to write:
  build_system() -> (ControlSystem, list[Rule])   # rules created with label='A1'...'A6'
  run(cgpa, probation_count) -> (risk_score: float, simulation, rules)
Rule IDs MUST match data/traceability.csv (enforced by tests/test_config_traceability.py).
"""
