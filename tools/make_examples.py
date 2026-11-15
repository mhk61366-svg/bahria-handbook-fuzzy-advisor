"""Generate worked examples document for the Bahria Handbook Fuzzy Advisor."""
from pathlib import Path

from src.engine import FuzzyAdvisor

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT / "worked_examples.md"


def make_examples() -> None:
    """Generate worked_examples.md covering at least 10 diverse query cases."""
    advisor = FuzzyAdvisor()

    examples = [
        {"domain": "probation", "inputs": {"cgpa": 3.75, "probation_count": 0}, "desc": "High academic achiever in good standing with zero probations."},
        {"domain": "probation", "inputs": {"cgpa": 2.20, "probation_count": 0}, "desc": "Satisfactory performance safely above probation threshold."},
        {"domain": "probation", "inputs": {"cgpa": 2.00, "probation_count": 0}, "desc": "Exact probation threshold boundary in good standing."},
        {"domain": "probation", "inputs": {"cgpa": 1.99, "probation_count": 0}, "desc": "Just below threshold placed on first probation."},
        {"domain": "probation", "inputs": {"cgpa": 1.95, "probation_count": 1}, "desc": "Second consecutive semester below threshold placed on probation 2."},
        {"domain": "probation", "inputs": {"cgpa": 1.80, "probation_count": 2}, "desc": "Third consecutive failure resulting in academic drop."},
        {"domain": "probation", "inputs": {"cgpa": 2.05, "probation_count": 2}, "desc": "Student with two previous probations recovering to good standing."},
        {"domain": "scholarship", "inputs": {"cgpa": 3.90, "scholarship_type": "merit_batch_topper", "credit_hours": 15}, "desc": "Batch topper merit scholarship with strong GPA and full course load."},
        {"domain": "scholarship", "inputs": {"cgpa": 3.75, "scholarship_type": "merit_batch_topper", "credit_hours": 12}, "desc": "Merit scholarship at exact retention boundary with regular load."},
        {"domain": "scholarship", "inputs": {"cgpa": 3.74, "scholarship_type": "merit_batch_topper", "credit_hours": 12}, "desc": "Merit scholarship just below threshold resulting in suspension."},
        {"domain": "scholarship", "inputs": {"cgpa": 3.60, "scholarship_type": "advance_merit_continuation", "credit_hours": 15}, "desc": "Advance merit scholarship continuation comfortably above threshold."},
        {"domain": "scholarship", "inputs": {"cgpa": 2.70, "scholarship_type": "financial_assistance", "credit_hours": 12}, "desc": "Financial assistance scholarship safely retained."},
        {"domain": "scholarship", "inputs": {"cgpa": 3.80, "scholarship_type": "merit_batch_topper", "credit_hours": 8.0}, "desc": "High GPA student with under-load credit hours risking scholarship suspension."},
    ]

    lines = [
        "# Worked Examples: Bahria Handbook Fuzzy Advisor",
        "",
        "This document contains worked evaluation examples across Domain A (Probation & Drop) and Domain B (Scholarship Retention).",
        "",
    ]

    for idx, ex in enumerate(examples, start=1):
        domain = ex["domain"]
        res = advisor.evaluate(domain, **ex["inputs"])

        lines.append(f"## Example {idx}")
        lines.append(f"*{ex['desc']}*")
        lines.append("")
        lines.append(f"- **Domain**: {domain.capitalize()}")
        lines.append(f"- **Inputs**: {res.inputs}")
        lines.append(f"- **Official verdict**: {res.verdict.label} ({', '.join(res.verdict.clauses)})")
        lines.append(f"- **Risk score**: {res.risk_score:.2f} / 100 (Band: {res.risk_label})")
        lines.append(f"- **Interpretation**: {res.advice}")
        lines.append("- **Fired rules**:")
        if res.fired_rules:
            for fr in res.fired_rules:
                lines.append(f"  - `{fr.rule_id}`: {fr.text} (strength: {fr.strength:.3f}, source: {fr.source})")
        else:
            lines.append("  - None")
        lines.append("")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    make_examples()
