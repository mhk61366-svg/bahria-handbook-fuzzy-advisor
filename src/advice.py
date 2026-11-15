"""Human-readable interpretation and advice composition."""
from typing import Any
import skfuzzy as fuzz

from src import config
from src.models import Verdict
from src.variables import risk_consequent

_RISK_VAR = risk_consequent()


def risk_label(score: float) -> str:
    """Return the output term with the highest membership at the crisp score.

    Ties go to the more severe term (order in config.RISK_TERMS).
    """
    universe = _RISK_VAR.universe
    best_term = config.RISK_TERMS[0]
    best_mu = -1.0

    for term in config.RISK_TERMS:
        mu = float(fuzz.interp_membership(universe, _RISK_VAR[term].mf, score))
        mu_rounded = round(mu, 6)
        if mu_rounded >= best_mu:
            best_mu = mu_rounded
            best_term = term

    return best_term


def compose_advice(
    domain: str,
    verdict: Verdict,
    risk_label: str,
    inputs: dict[str, Any],
) -> str:
    """Compose human-readable advice for the student.

    Always states the official verdict first (label and handbook clauses),
    followed by the fuzzy risk sentence containing the risk label.
    """
    clauses_str = ", ".join(verdict.clauses)
    official_part = f"Official status: {verdict.label} ({clauses_str})."

    if domain == "probation":
        risk_messages = {
            "low": "Fuzzy risk is low: academic standing is secure with no immediate risk of probation.",
            "moderate": "Fuzzy risk is moderate: performance is near the minimum threshold; monitor coursework closely.",
            "high": "Fuzzy risk is high: substantial risk of academic probation or drop; immediate improvement is required.",
            "critical": "Fuzzy risk is critical: imminent risk of academic drop; consult your academic advisor immediately.",
        }
    else:
        risk_messages = {
            "low": "Fuzzy risk is low: scholarship retention criteria are fully satisfied.",
            "moderate": "Fuzzy risk is moderate: close to retention threshold or minimum course load; monitor GPA and credit hours.",
            "high": "Fuzzy risk is high: significant risk of scholarship suspension due to GPA or course load.",
            "critical": "Fuzzy risk is critical: scholarship is subject to immediate suspension.",
        }

    risk_part = risk_messages.get(
        risk_label,
        f"Fuzzy risk is {risk_label}.",
    )

    return f"{official_part} {risk_part}"
