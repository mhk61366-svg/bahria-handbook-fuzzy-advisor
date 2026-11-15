"""Domain A: probation and drop (handbook §5.5, p.71-72)."""
from skfuzzy import control as ctrl
from src import config
from src.models import RuleBaseNotReady
from src.variables import cgpa_antecedent, probation_count_antecedent, risk_consequent

# ======================= HUMAN-OWNED BLOCK: START =======================
# Agent: do not edit anything between these markers.
def make_rules(cgpa, probation_count, risk) -> list[ctrl.Rule]:   # scholarship: (cgpa, credit_load, risk)
    return []        # the human writes rules here, e.g. ctrl.Rule(cgpa["safe"], risk["low"], label="A1")

RULE_REFS: dict[str, str] = {}      # e.g. {"A1": "§5.5.1, p.71"}
# ======================== HUMAN-OWNED BLOCK: END ========================


def build_system() -> tuple[ctrl.ControlSystem, list[ctrl.Rule]]:
    """Build the probation control system and return (system, rules)."""
    cgpa = cgpa_antecedent(config.PROBATION_MIN_CGPA)
    probation_count = probation_count_antecedent()
    risk = risk_consequent()

    rules = make_rules(cgpa, probation_count, risk)
    if not rules:
        raise RuleBaseNotReady("Probation rule base is empty.")

    system = ctrl.ControlSystem(rules)
    return system, rules
