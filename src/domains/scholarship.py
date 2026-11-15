"""Domain B: scholarship retention (handbook §4.3.2.2, §4.4.3, §4.5, §4.11)."""
from skfuzzy import control as ctrl

from src import config
from src.models import RuleBaseNotReady
from src.variables import cgpa_antecedent, credit_load_antecedent, risk_consequent

# ======================= HUMAN-OWNED BLOCK: START =======================
# Agent: do not edit anything between these markers.
def make_rules(cgpa, credit_load, risk) -> list[ctrl.Rule]:
    return [
        ctrl.Rule(cgpa["safe"] & credit_load["regular"], risk["low"], label="B1"),
        ctrl.Rule(cgpa["borderline"] & credit_load["regular"], risk["moderate"], label="B2"),
        ctrl.Rule(cgpa["below_min"], risk["high"], label="B3"),
        ctrl.Rule(credit_load["under_load"], risk["high"], label="B4"),
    ]


RULE_REFS: dict[str, str] = {
    "B1": "§4.3.3.1.2(b), §4.3.4.2, pp.50-51; §4.4.3.3, p.52; §4.5.3(d), p.53",
    "B2": "derived from §4.11, p.55",
    "B3": "§4.11, §4.12(d), p.55",
    "B4": "§4.4.3.5, p.52; §4.12(b), p.55",
}
# ======================== HUMAN-OWNED BLOCK: END ========================


def build_system(scholarship_type: str) -> tuple[ctrl.ControlSystem, list[ctrl.Rule]]:
    """Build the scholarship control system for scholarship_type and return (system, rules)."""
    threshold = config.SCHOLARSHIP_THRESHOLDS[scholarship_type]
    cgpa = cgpa_antecedent(threshold)
    credit_load = credit_load_antecedent()
    risk = risk_consequent()

    rules = make_rules(cgpa, credit_load, risk)
    if not rules:
        raise RuleBaseNotReady(f"Scholarship rule base is empty for {scholarship_type}.")

    system = ctrl.ControlSystem(rules)
    return system, rules
