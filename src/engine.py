"""Single evaluation engine orchestrating validation, crisp rules, and fuzzy inference."""
from typing import Any
import skfuzzy.control as ctrl

from src.advice import compose_advice, risk_label
from src.crisp_rules import probation_verdict, scholarship_verdict
from src.domains import probation, scholarship
from src.explain import fired_rules
from src.models import AdvisorResult
from src.validation import (
    InputError,
    validate_cgpa,
    validate_credit_hours,
    validate_probation_count,
    validate_scholarship_type,
)


class FuzzyAdvisor:
    """Evaluates student academic queries across probation and scholarship domains."""

    def evaluate(self, domain: str, **raw_inputs: Any) -> AdvisorResult:
        """Evaluate a student query.

        Execution order:
            1. Validate inputs (domain, keys, values)
            2. Official crisp verdict
            3. Fuzzy inference (risk score)
            4. Rule explainability (fired rules with strengths)
            5. Risk label and advice text composition
        """
        if not isinstance(domain, str) or domain.strip() not in ("probation", "scholarship"):
            raise InputError(
                f"Unknown domain {domain!r}. Allowed domains: 'probation', 'scholarship'."
            )
        domain_clean = domain.strip()

        if domain_clean == "probation":
            expected_keys = {"cgpa", "probation_count"}
            actual_keys = set(raw_inputs.keys())
            missing = expected_keys - actual_keys
            unexpected = actual_keys - expected_keys
            if missing:
                raise InputError(
                    f"Missing required input(s) for probation: {sorted(missing)}."
                )
            if unexpected:
                raise InputError(
                    f"Unexpected input(s) for probation: {sorted(unexpected)}."
                )

            cgpa = validate_cgpa(raw_inputs["cgpa"])
            probation_count = validate_probation_count(raw_inputs["probation_count"])
            validated_inputs: dict[str, Any] = {
                "cgpa": cgpa,
                "probation_count": probation_count,
            }

            verdict = probation_verdict(cgpa=cgpa, probation_count=probation_count)

            system, rules = probation.build_system()
            sim = ctrl.ControlSystemSimulation(system)
            sim.input["cgpa"] = cgpa
            sim.input["probation_count"] = probation_count
            sim.compute()

            risk_score = float(sim.output["risk"])
            fired = fired_rules(sim, rules, probation.RULE_REFS)

        else:
            expected_keys = {"cgpa", "scholarship_type", "credit_hours"}
            actual_keys = set(raw_inputs.keys())
            missing = expected_keys - actual_keys
            unexpected = actual_keys - expected_keys
            if missing:
                raise InputError(
                    f"Missing required input(s) for scholarship: {sorted(missing)}."
                )
            if unexpected:
                raise InputError(
                    f"Unexpected input(s) for scholarship: {sorted(unexpected)}."
                )

            cgpa = validate_cgpa(raw_inputs["cgpa"])
            scholarship_type = validate_scholarship_type(raw_inputs["scholarship_type"])
            credit_hours = validate_credit_hours(raw_inputs["credit_hours"])
            validated_inputs = {
                "cgpa": cgpa,
                "scholarship_type": scholarship_type,
                "credit_hours": credit_hours,
            }

            verdict = scholarship_verdict(
                cgpa=cgpa,
                scholarship_type=scholarship_type,
            )

            system, rules = scholarship.build_system(scholarship_type)
            sim = ctrl.ControlSystemSimulation(system)
            sim.input["cgpa"] = cgpa
            sim.input["credit_load"] = credit_hours
            sim.compute()

            risk_score = float(sim.output["risk"])
            fired = fired_rules(sim, rules, scholarship.RULE_REFS)

        r_label = risk_label(risk_score)
        advice_text = compose_advice(
            domain=domain_clean,
            verdict=verdict,
            risk_label=r_label,
            inputs=validated_inputs,
        )

        return AdvisorResult(
            domain=domain_clean,
            inputs=validated_inputs,
            verdict=verdict,
            risk_score=risk_score,
            risk_label=r_label,
            fired_rules=fired,
            advice=advice_text,
            warnings=[],
        )
