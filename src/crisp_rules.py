"""The handbook as plain Python: the OFFICIAL verdict. No skfuzzy imports."""
from src import config
from src.models import Verdict


def probation_verdict(cgpa: float, probation_count: int) -> Verdict:
    """Compute official probation verdict based on handbook section 5.5.

    cgpa >= 2.00                      -> GOOD_STANDING  (§5.5.1, §5.5.4)
    cgpa <  2.00 and count == 0       -> PROBATION_1    (§5.5.1)
    cgpa <  2.00 and count == 1       -> PROBATION_2    (§5.5.1, §5.5.5)
    cgpa <  2.00 and count == 2       -> DROP           (§5.5.3)
    """
    if probation_count not in config.PROBATION_COUNTS:
        raise ValueError(f"Invalid probation count: {probation_count}")

    if cgpa >= config.PROBATION_MIN_CGPA:
        return Verdict(
            code="GOOD_STANDING",
            label="Good standing",
            clauses=("§5.5.1", "§5.5.4"),
        )
    if probation_count == 0:
        return Verdict(
            code="PROBATION_1",
            label="Probation 1",
            clauses=("§5.5.1",),
        )
    if probation_count == 1:
        return Verdict(
            code="PROBATION_2",
            label="Probation 2",
            clauses=("§5.5.1", "§5.5.5"),
        )
    return Verdict(
        code="DROP",
        label="Drop",
        clauses=("§5.5.3",),
    )


def scholarship_verdict(cgpa: float, scholarship_type: str) -> Verdict:
    """Compute official scholarship verdict based on handbook sections 4.3-4.11.

    cgpa >= threshold -> ELIGIBLE
    cgpa <  threshold -> SUSPENDED
    """
    if scholarship_type not in config.SCHOLARSHIP_THRESHOLDS:
        raise KeyError(f"Unknown scholarship type: {scholarship_type}")

    threshold = config.SCHOLARSHIP_THRESHOLDS[scholarship_type]

    clauses_by_type = {
        "merit_batch_topper": {
            "eligible": ("§4.4.3.3",),
            "suspended": ("§4.4.3.3", "§4.11"),
        },
        "advance_merit_continuation": {
            "eligible": ("§4.3.2.2", "§4.3.3.1.2(b)"),
            "suspended": ("§4.3.2.2", "§4.3.3.1.2(b)", "§4.11"),
        },
        "financial_assistance": {
            "eligible": ("§4.5.2", "§4.5.3(d)"),
            "suspended": ("§4.5.2", "§4.5.3(d)", "§4.11"),
        },
    }

    if cgpa >= threshold:
        return Verdict(
            code="ELIGIBLE",
            label="Eligible",
            clauses=clauses_by_type[scholarship_type]["eligible"],
        )
    return Verdict(
        code="SUSPENDED",
        label="Suspended",
        clauses=clauses_by_type[scholarship_type]["suspended"],
    )
