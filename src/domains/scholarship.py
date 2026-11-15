"""Domain B: scholarship retention (handbook §4.3.2.2, §4.4.3, §4.5, §4.11)."""
from skfuzzy import control as ctrl

from src import config
from src.models import RuleBaseNotReady
from src.variables import cgpa_antecedent, credit_load_antecedent, risk_consequent

# ======================= HUMAN-OWNED BLOCK: START =======================
# Agent: do not edit anything between these markers.
def make_rules(cgpa, credit_load, risk) -> list[ctrl.Rule]:   # scholarship: (cgpa, credit_load, risk)
    return []        # the human writes rules here, e.g. ctrl.Rule(cgpa["safe"], risk["low"], label="A1")

RULE_REFS: dict[str, str] = {}      # e.g. {"A1": "§5.5.1, p.71"}
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
