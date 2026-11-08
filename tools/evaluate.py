"""Run data/test_queries.csv through FuzzyAdvisor.

Contents to write:
  for each row: run engine (catch InputError -> outcome 'ERROR'); compare to expected_outcome / expected_risk_band;
  write report/test_results.csv (input, expected, actual, PASS/FAIL);
  print total, passed, accuracy and the list of failures (feeds the failure-analysis section of the report).
"""
