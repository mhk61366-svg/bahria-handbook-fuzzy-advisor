"""Evaluation runner: reads data/test_queries.csv and produces test_results.csv."""
import csv
from pathlib import Path

from src.engine import FuzzyAdvisor
from src.validation import InputError

ROOT = Path(__file__).resolve().parent.parent
INPUT_CSV = ROOT / "data" / "test_queries.csv"
OUTPUT_CSV = ROOT / "test_results.csv"


def run_evaluation() -> None:
    """Run test queries against FuzzyAdvisor and report pass/fail status."""
    advisor = FuzzyAdvisor()
    results = []
    total = 0
    passed = 0
    failures = []

    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            row_id = row["id"]
            category = row["category"]
            domain = row["domain"]
            expected_outcome = row["expected_outcome"]
            expected_risk_band = row["expected_risk_band"]

            if domain == "probation":
                raw_inputs = {
                    "cgpa": row["cgpa"],
                    "probation_count": row["probation_count"],
                }
                inputs_str = f"domain={domain}, cgpa={row['cgpa']}, probation_count={row['probation_count']}"
            else:
                raw_inputs = {
                    "cgpa": row["cgpa"],
                    "scholarship_type": row["scholarship_type"],
                    "credit_hours": row["credit_hours"],
                }
                inputs_str = (
                    f"domain={domain}, cgpa={row['cgpa']}, "
                    f"scholarship_type={row['scholarship_type']}, credit_hours={row['credit_hours']}"
                )

            try:
                res = advisor.evaluate(domain, **raw_inputs)
                actual_outcome = res.verdict.code
                actual_risk_band = res.risk_label
            except InputError:
                actual_outcome = "ERROR"
                actual_risk_band = ""

            outcome_match = (actual_outcome == expected_outcome)
            if expected_outcome == "ERROR":
                risk_match = True
            else:
                risk_match = (actual_risk_band == expected_risk_band)

            if outcome_match and risk_match:
                result = "PASS"
                passed += 1
            else:
                result = "FAIL"
                failures.append(
                    f"[{row_id}] {inputs_str} -> Expected: ({expected_outcome}, {expected_risk_band}), "
                    f"Got: ({actual_outcome}, {actual_risk_band})"
                )

            results.append({
                "id": row_id,
                "category": category,
                "inputs": inputs_str,
                "expected_outcome": expected_outcome,
                "actual_outcome": actual_outcome,
                "expected_risk_band": expected_risk_band,
                "actual_risk_band": actual_risk_band,
                "result": result,
            })

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "id",
            "category",
            "inputs",
            "expected_outcome",
            "actual_outcome",
            "expected_risk_band",
            "actual_risk_band",
            "result",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    accuracy = (passed / total * 100) if total > 0 else 0.0
    print(f"Total: {total}")
    print(f"Passed: {passed}")
    print(f"Accuracy: {accuracy:.1f}%")

    if failures:
        print("\nFailures:")
        for fail in failures:
            print(f"  - {fail}")


if __name__ == "__main__":
    run_evaluation()
