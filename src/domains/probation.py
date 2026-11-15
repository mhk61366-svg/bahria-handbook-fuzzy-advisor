"""Domain A: probation and drop (handbook §5.5, p.71-72)."""
from skfuzzy import control as ctrl
from src import config
from src.models import RuleBaseNotReady
from src.variables import cgpa_antecedent, probation_count_antecedent, risk_consequent

# ======================= HUMAN-OWNED BLOCK: START =======================
# Agent: do not edit anything between these markers.

def make_rules(cgpa, probation_count, risk) -> list[ctrl.Rule]:
    return [
        ctrl.Rule(cgpa["safe"] & probation_count["none"], risk["low"], label="A1"),
        ctrl.Rule(cgpa["borderline"] & probation_count["none"], risk["moderate"], label="A2"),
        ctrl.Rule(cgpa["below_min"] & probation_count["none"], risk["high"], label="A3"),
        ctrl.Rule(cgpa["below_min"] & probation_count["first"], risk["critical"], label="A4"),
        ctrl.Rule(cgpa["below_min"] & probation_count["second"], risk["critical"], label="A5"),
        ctrl.Rule(cgpa["safe"] & (probation_count["first"] | probation_count["second"]), risk["low"], label="A6"),
        ctrl.Rule(cgpa["borderline"] & probation_count["first"], risk["high"], label="A7"),
        ctrl.Rule(cgpa["borderline"] & probation_count["second"], risk["critical"], label="A8"),
    ]


RULE_REFS: dict[str, str] = {
    "A1": "§5.5.1, p.71; §2.21.1, p.35",
    "A2": "derived from §5.5.1, p.71; §5.17.2, p.78",
    "A3": "§1.1.25, p.4; §5.5.1-5.5.2, p.71",
    "A4": "§5.5.1, §5.5.2, §5.5.5, pp.71-72",
    "A5": "§1.1.8, p.2; §5.5.3, p.71",
    "A6": "§5.5.4, p.71",
    "A7": "derived from §5.5.1, §5.5.3, p.71",
    "A8": "derived from §5.5.3, p.71",
}

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
