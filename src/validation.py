"""Input validation. Raise InputError with a student-readable message. NEVER clamp silently.

Contents to write:
  class InputError(ValueError)
  parse_float(raw) -> float            # reject '', 'abc', 'nan', 'inf', decimal comma
  validate_cgpa(raw) -> float          # 0.00 <= x <= 4.00 (config.CGPA_MIN/MAX)
  validate_probation_count(raw) -> int # one of config.PROBATION_COUNTS
  validate_credit_hours(raw) -> float  # 0 <= x <= config.CREDITS_MAX
  validate_scholarship_type(raw) -> str# key of config.SCHOLARSHIP_THRESHOLDS
Used by engine.py before any fuzzy computation, and by the GUI to show errors.
"""
