"""Single entry point used by GUI, tests and tools. Orchestrates; contains no membership-function details.

Contents to write:
  class FuzzyAdvisor:
      evaluate(domain: str, **raw_inputs) -> AdvisorResult
          1. validate (validation.py)           -> InputError on bad input
          2. official verdict (crisp_rules.py)
          3. fuzzy risk (domains/*)             -> crisp score
          4. fired rules (explain.py)
          5. label + advice (advice.py)
"""
