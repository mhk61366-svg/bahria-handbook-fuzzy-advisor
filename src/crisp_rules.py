"""The handbook as plain Python: the OFFICIAL verdict. No skfuzzy imports.

Contents to write:
  probation_verdict(cgpa, probation_count) -> Verdict
      cgpa >= 2.00                      -> GOOD_STANDING  (5.5.1, 5.5.4: count resets)
      cgpa <  2.00 and count == 0       -> PROBATION_1    (5.5.1)
      cgpa <  2.00 and count == 1       -> PROBATION_2    (5.5.1, 5.5.5)
      cgpa <  2.00 and count == 2       -> DROP           (5.5.3)
  scholarship_verdict(cgpa, scholarship_type) -> Verdict
      cgpa >= threshold -> ELIGIBLE ; cgpa < threshold -> SUSPENDED   (4.4.3.3, 4.5.3(d), 4.11)
Boundary rule: a value exactly equal to the threshold MEETS the requirement.
This module is the ground truth the tests compare against.
"""
