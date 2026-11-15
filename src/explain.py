"""Explainability: extraction and independent computation of fired rules."""
from typing import Any
import skfuzzy as fuzz
from skfuzzy.control.rule import Rule
from skfuzzy.control.controlsystem import ControlSystemSimulation
from skfuzzy.control.term import Term, TermAggregate

from src.models import FiredRule


def fired_rules(
    sim: ControlSystemSimulation,
    rules: list[Rule],
    rule_refs: dict[str, str],
) -> list[FiredRule]:
    """Extract rules that fired with non-zero strength, sorted descending.

    Reads rule.aggregate_firing[sim] immediately after sim.compute().
    """
    fired: list[FiredRule] = []
    for rule in rules:
        try:
            strength = float(rule.aggregate_firing[sim])
        except (KeyError, AttributeError):
            strength = 0.0
        if strength > 0.0:
            label = rule.label or ""
            consequent_text = ", ".join(str(c) for c in rule.consequent)
            text = f"IF {rule.antecedent} THEN {consequent_text}"
            source = rule_refs.get(label, "")
            fired.append(
                FiredRule(
                    rule_id=label,
                    text=text,
                    strength=strength,
                    source=source,
                )
            )

    fired.sort(key=lambda r: r.strength, reverse=True)
    return fired


def _evaluate_node(node: Any, inputs: dict[str, float]) -> float:
    """Recursively evaluate an antecedent node (Term or TermAggregate)."""
    if isinstance(node, Term):
        var_name = node.parent.label
        val = float(inputs[var_name])
        return float(fuzz.interp_membership(node.parent.universe, node.mf, val))
    if isinstance(node, TermAggregate):
        if node.kind == "and":
            return min(_evaluate_node(node.term1, inputs), _evaluate_node(node.term2, inputs))
        if node.kind == "or":
            return max(_evaluate_node(node.term1, inputs), _evaluate_node(node.term2, inputs))
        if node.kind == "not":
            return 1.0 - _evaluate_node(node.term1, inputs)
        raise ValueError(f"Unknown aggregate kind: {node.kind!r}")
    raise TypeError(f"Unknown antecedent node type: {type(node)!r}")


def independent_strengths(
    inputs: dict[str, float],
    rules: list[Rule],
) -> dict[str, float]:
    """Compute rule firing strengths independently using interp_membership.

    Keys are rule labels and include zero strengths.
    Inputs is keyed by variable name (e.g. 'cgpa', 'probation_count', 'credit_load').
    """
    strengths: dict[str, float] = {}
    for rule in rules:
        label = rule.label or ""
        strengths[label] = _evaluate_node(rule.antecedent, inputs)
    return strengths
