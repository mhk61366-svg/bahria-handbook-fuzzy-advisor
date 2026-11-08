"""Human-readable interpretation. Wording lives here so it can be edited without touching logic.

Contents to write:
  risk_label(score) -> str                 # term with highest membership at the crisp score; ties -> more severe
  compose_advice(domain, verdict, risk_label, inputs) -> str
      always states the OFFICIAL verdict first (with clause), then the fuzzy risk sentence.
      e.g. "Official status: ON PROBATION (5.5.1). Fuzzy risk: moderate - you are just under the line."
"""
