"""Plain dataclasses shared across the package. No skfuzzy imports.

Contents to write:
  @dataclass(frozen=True) Verdict:     code: str, label: str, clauses: tuple[str, ...]
  @dataclass(frozen=True) FiredRule:   rule_id: str, text: str, strength: float, source: str
  @dataclass AdvisorResult:            domain: str, inputs: dict, verdict: Verdict, risk_score: float,
                                       risk_label: str, fired_rules: list[FiredRule], advice: str,
                                       warnings: list[str]
"""
