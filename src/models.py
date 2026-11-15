# Plain data classes and exceptions shared across the package. No skfuzzy imports.
from dataclasses import dataclass, field
from typing import Any


class RuleBaseNotReady(RuntimeError):
    """Raised when a domain rule base is empty or incomplete."""


@dataclass(frozen=True)
class Verdict:
    # Official handbook verdict.

    code: str
    label: str
    clauses: tuple[str, ...]


@dataclass(frozen=True)
class FiredRule:
    # A fuzzy rule that fired with non-zero strength.

    rule_id: str
    text: str
    strength: float
    source: str


@dataclass
class AdvisorResult:
    # Complete evaluation result for a student query.

    domain: str
    inputs: dict[str, Any]
    verdict: Verdict
    risk_score: float
    risk_label: str
    fired_rules: list[FiredRule]
    advice: str
    warnings: list[str] = field(default_factory=list)
