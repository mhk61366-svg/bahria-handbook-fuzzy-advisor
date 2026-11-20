from __future__ import annotations

import ast
import inspect
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import skfuzzy as fuzz
from skfuzzy import control as ctrl

from src import advice, config, crisp_rules, engine, explain, models, validation, variables
from src.domains import probation, scholarship

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TYPES = list(config.SCHOLARSHIP_THRESHOLDS)
SEVERITY = {term: idx for idx, term in enumerate(config.RISK_TERMS)}


# ----------------------------------------------------------------- helpers --
def done(problems: list[str]) -> None:
    assert not problems, "\n - " + "\n - ".join(problems)


def py_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*.py") if "__pycache__" not in p.parts)


def call_fired_rules(
    sim: ctrl.ControlSystemSimulation,
    rules: list[ctrl.Rule],
    rule_refs: dict[str, str],
) -> list[models.FiredRule]:
    params = list(inspect.signature(explain.fired_rules).parameters.values())
    if len(params) >= 3:
        return explain.fired_rules(sim, rules, rule_refs)
    return explain.fired_rules(sim, rules)


def call_compose_advice(
    domain: str,
    verdict: models.Verdict,
    r_label: str,
    inputs: dict[str, Any],
) -> str:
    params = list(inspect.signature(advice.compose_advice).parameters.values())
    if len(params) >= 4:
        return advice.compose_advice(domain, verdict, r_label, inputs)
    return advice.compose_advice(domain, verdict, r_label)


def eval_scholarship(
    advisor: engine.FuzzyAdvisor,
    cgpa: Any,
    scholarship_type: Any,
    credit_hours: Any,
) -> models.AdvisorResult:
    try:
        return advisor.evaluate(
            "scholarship",
            cgpa=cgpa,
            scholarship_type=scholarship_type,
            credit_hours=credit_hours,
        )
    except (TypeError, validation.InputError) as exc:
        msg = str(exc).lower()
        if "credit_load" in msg or "unexpected keyword" in msg:
            return advisor.evaluate(
                "scholarship",
                cgpa=cgpa,
                scholarship_type=scholarship_type,
                credit_load=credit_hours,
            )
        raise


def oracle_rule_strength(rule: ctrl.Rule, inputs: dict[str, float]) -> float:
    """Reference recursive evaluator for scikit-fuzzy Term / TermAggregate trees."""

    def eval_node(node: Any) -> float:
        if isinstance(node, ctrl.term.Term):
            var = node.parent
            x = float(inputs[var.label])
            return float(fuzz.interp_membership(var.universe, node.mf, x))
        if isinstance(node, ctrl.term.TermAggregate):
            left = eval_node(node.term1)
            right = eval_node(node.term2)
            if node.kind == "and":
                return min(left, right)
            if node.kind == "or":
                return max(left, right)
            raise ValueError(f"Unsupported TermAggregate kind: {node.kind!r}")
        raise TypeError(f"Unsupported antecedent node type: {type(node).__name__}")

    return eval_node(rule.antecedent)


# ========================================== 1-2 hygiene & architecture ======
STAGE2_WRITTEN = [
    "explain.py",
    "advice.py",
    "engine.py",
    "domains/probation.py",
    "domains/scholarship.py",
]
ALLOWED_THIRD_PARTY = {"src", "numpy", "scipy", "networkx", "matplotlib", "skfuzzy", "pytest"}


def test_01_stage2_files_implemented_and_stub_free():
    """Stage 2 modules exist, have no scaffold stub text or print(), and use only allowed imports."""
    problems: list[str] = []
    stdlib = set(sys.stdlib_module_names)
    for name in STAGE2_WRITTEN:
        path = SRC / name
        if not path.is_file():
            problems.append(f"src/{name} is missing")
            continue
        text = path.read_text(encoding="utf-8")
        if "Contents to write" in text:
            problems.append(f"src/{name} still contains the scaffold 'Contents to write' stub docstring")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                problems.append(f"src/{name}:{node.lineno} uses print() in library code")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top not in stdlib and top not in ALLOWED_THIRD_PARTY:
                        problems.append(f"src/{name} imports disallowed package '{top}'")
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                top = node.module.split(".")[0]
                if top not in stdlib and top not in ALLOWED_THIRD_PARTY:
                    problems.append(f"src/{name} imports disallowed package '{top}'")
    for mod, attrs in (
        (explain, ("fired_rules", "independent_strengths")),
        (advice, ("risk_label", "compose_advice")),
        (engine, ("FuzzyAdvisor",)),
    ):
        for attr in attrs:
            if not hasattr(mod, attr):
                problems.append(f"{mod.__name__}.{attr} is missing")
    done(problems)


def test_02_architectural_isolation_aggregate_firing_and_crisp_rules():
    """Only explain.py may touch rule.aggregate_firing; no traceability.csv; crisp_rules stays skfuzzy-free."""
    problems: list[str] = []
    explain_touches_agg = False
    for path in py_files(SRC):
        rel = path.relative_to(SRC).as_posix()
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        touches_agg = any(
            (isinstance(n, ast.Attribute) and n.attr == "aggregate_firing")
            or (isinstance(n, ast.Constant) and n.value == "aggregate_firing")
            for n in ast.walk(tree)
        )
        if rel == "explain.py":
            explain_touches_agg = touches_agg
        elif touches_agg:
            problems.append(f"src/{rel} accesses 'aggregate_firing' (AGENTS.md §6.3: ONLY explain.py may touch it)")
        if rel in STAGE2_WRITTEN and "traceability.csv" in text:
            problems.append(f"src/{rel} references dropped 'traceability.csv' (AGENTS.md §2 override 1)")
    if not explain_touches_agg:
        problems.append("src/explain.py does not read rule.aggregate_firing[sim] as required by AGENTS.md §6.3")

    proc = subprocess.run(
        [sys.executable, "-c", "import sys, src.crisp_rules; print('skfuzzy' in sys.modules)"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or proc.stdout.strip() != "False":
        problems.append("src.crisp_rules must remain completely free of scikit-fuzzy imports")
    done(problems)


# ========================================== 3-4 rule base audit & coverage ==
def test_03_human_rule_base_populated_and_rule_refs_complete():
    """Both domains have populated rules, unique A#/B# labels, matching RULE_REFS, and valid risk terms."""
    problems: list[str] = []
    try:
        _, a_rules = probation.build_system()
    except Exception as exc:  # noqa: BLE001
        problems.append(f"probation.build_system() failed: {type(exc).__name__}: {exc}")
        a_rules = []

    try:
        _, b_rules = scholarship.build_system(TYPES[0])
    except Exception as exc:  # noqa: BLE001
        problems.append(f"scholarship.build_system({TYPES[0]!r}) failed: {type(exc).__name__}: {exc}")
        b_rules = []

    for dom_name, prefix, rules, refs, expect_all_terms in (
        ("probation", "A", a_rules, probation.RULE_REFS, True),
        ("scholarship", "B", b_rules, scholarship.RULE_REFS, False),
    ):
        if not rules:
            problems.append(f"{dom_name}: rule base is empty")
            continue
        labels = [getattr(r, "label", None) for r in rules]
        if not all(isinstance(lb, str) and lb.startswith(prefix) and lb[1:].isdigit() for lb in labels):
            problems.append(f"{dom_name}: rule labels must be {prefix}1, {prefix}2, ..., got {labels}")
        if len(set(labels)) != len(labels):
            problems.append(f"{dom_name}: duplicate rule labels in {labels}")
        missing_refs = sorted(set(labels) - set(refs.keys()))
        orphan_refs = sorted(set(refs.keys()) - set(labels))
        if missing_refs:
            problems.append(f"{dom_name}: rules missing from RULE_REFS: {missing_refs}")
        if orphan_refs:
            problems.append(f"{dom_name}: RULE_REFS keys with no matching rule: {orphan_refs}")
        if any(not isinstance(refs.get(lb), str) or not refs[lb].strip() for lb in labels if lb in refs):
            problems.append(f"{dom_name}: every RULE_REFS value must be a non-empty handbook citation string")

        consequent_terms: set[str] = set()
        for r in rules:
            cons = r.consequent
            items = cons if isinstance(cons, (list, tuple)) else [cons]
            for item in items:
                term_obj = getattr(item, "term", item)
                t_label = getattr(term_obj, "label", None)
                if t_label in config.RISK_TERMS:
                    consequent_terms.add(t_label)
                else:
                    problems.append(f"{dom_name} rule {r.label}: unknown consequent term {t_label!r}")
        if expect_all_terms and consequent_terms != set(config.RISK_TERMS):
            problems.append(
                f"{dom_name}: rules produce {sorted(consequent_terms)}, expected all of {list(config.RISK_TERMS)}"
            )
        elif not expect_all_terms and not {"low", "moderate", "high"}.issubset(consequent_terms):
            problems.append(f"{dom_name}: rules must produce at least low, moderate, and high risk terms")
    done(problems)


def test_04_rule_base_cgpa_coverage_and_scholarship_type_anchoring():
    """Every CGPA/input combination fires >=1 rule; Domain B shares rule structure across types with per-type T."""
    problems: list[str] = []
    cgpa_grid = [0.0, 0.5, 1.67, 1.85, 1.99, 2.0, 2.01, 2.33, 2.5, 3.0, 3.5, 3.75, 4.0]

    try:
        _, a_rules = probation.build_system()
        for count in config.PROBATION_COUNTS:
            for cgpa in cgpa_grid:
                strengths = [oracle_rule_strength(r, {"cgpa": cgpa, "probation_count": float(count)}) for r in a_rules]
                if max(strengths, default=0.0) <= 0.0:
                    problems.append(f"probation: no rule fires at CGPA={cgpa}, probation_count={count}")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"probation coverage check failed: {exc}")

    b_labels_by_type: dict[str, list[str]] = {}
    for stype in TYPES:
        try:
            _, b_rules = scholarship.build_system(stype)
            b_labels_by_type[stype] = [r.label for r in b_rules]
            for hours in (0.0, 6.0, 7.5, 9.0, 15.0, 18.0):
                for cgpa in cgpa_grid:
                    strengths = [oracle_rule_strength(r, {"cgpa": cgpa, "credit_load": hours}) for r in b_rules]
                    if max(strengths, default=0.0) <= 0.0:
                        problems.append(f"scholarship[{stype}]: no rule fires at CGPA={cgpa}, credit_load={hours}")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"scholarship[{stype}] coverage check failed: {exc}")

    if len({tuple(v) for v in b_labels_by_type.values()}) > 1:
        problems.append(f"Domain B rule labels differ across scholarship types: {b_labels_by_type}")
    done(problems)


# ========================================== 5-8 explain.py ==================
def test_05_fired_rules_positive_only_sorted_descending_with_refs():
    """fired_rules keeps only strength > 0, sorts descending, and populates rule_id, text, and source."""
    problems: list[str] = []
    sys_a, rules_a = probation.build_system()
    sim = ctrl.ControlSystemSimulation(sys_a)
    sim.input["cgpa"] = 1.85  # in (1.67, 2.00): both below_min and borderline are active
    sim.input["probation_count"] = 1
    sim.compute()

    fired = call_fired_rules(sim, rules_a, probation.RULE_REFS)
    if not fired or not all(isinstance(f, models.FiredRule) for f in fired):
        problems.append(f"fired_rules must return a non-empty list[FiredRule], got {fired!r}")
    else:
        strengths = [f.strength for f in fired]
        if any(s <= 0.0 or s > 1.0 + 1e-9 for s in strengths):
            problems.append(f"fired_rules must only include strengths in (0, 1], got {strengths}")
        if strengths != sorted(strengths, reverse=True):
            problems.append(f"fired_rules must be sorted descending by strength, got {strengths}")
        if len(fired) >= len(rules_a):
            problems.append("fired_rules included zero-strength rules (at CGPA=1.85, 'safe' rules have 0 strength)")
        for f in fired:
            if f.rule_id not in probation.RULE_REFS:
                problems.append(f"FiredRule.rule_id {f.rule_id!r} is not a known rule label")
            elif f.source != probation.RULE_REFS[f.rule_id]:
                problems.append(
                    f"FiredRule.source for {f.rule_id} is {f.source!r}, expected {probation.RULE_REFS[f.rule_id]!r}"
                )
            if not isinstance(f.text, str) or len(f.text.strip()) < 5 or "cgpa" not in f.text.lower():
                problems.append(f"FiredRule.text for {f.rule_id} does not look like rule text: {f.text!r}")
    done(problems)


def test_06_aggregate_firing_matches_independent_strengths_probation():
    """Domain A: rule.aggregate_firing[sim] and fired_rules match independent_strengths within 1e-6."""
    problems: list[str] = []
    sys_a, rules_a = probation.build_system()
    cgpas = [0.0, 1.5, 1.67, 1.80, 1.99, 2.00, 2.01, 2.15, 2.33, 3.50, 4.00]

    for count in config.PROBATION_COUNTS:
        for cgpa in cgpas:
            sim = ctrl.ControlSystemSimulation(sys_a)
            sim.input["cgpa"] = cgpa
            sim.input["probation_count"] = count
            sim.compute()

            inputs = {"cgpa": cgpa, "probation_count": count}
            ind = explain.independent_strengths(inputs, rules_a)
            fired = {f.rule_id: f.strength for f in call_fired_rules(sim, rules_a, probation.RULE_REFS)}

            if set(ind.keys()) != {r.label for r in rules_a}:
                problems.append(f"independent_strengths keys {sorted(ind)} != rule labels {[r.label for r in rules_a]}")
                break

            for r in rules_a:
                agg_val = float(r.aggregate_firing[sim])
                ind_val = float(ind[r.label])
                orc_val = oracle_rule_strength(r, inputs)
                if abs(agg_val - ind_val) > 1e-6 or abs(ind_val - orc_val) > 1e-6:
                    problems.append(
                        f"probation(cgpa={cgpa}, count={count}) rule {r.label}: "
                        f"aggregate_firing={agg_val:.6f}, independent={ind_val:.6f}, oracle={orc_val:.6f}"
                    )
                if agg_val > 1e-9 and abs(fired.get(r.label, -1.0) - agg_val) > 1e-6:
                    problems.append(
                        f"probation(cgpa={cgpa}, count={count}) rule {r.label}: "
                        f"missing or mismatched in fired_rules (got {fired.get(r.label)}, expected {agg_val:.6f})"
                    )
                if agg_val == 0.0 and r.label in fired:
                    problems.append(f"probation(cgpa={cgpa}, count={count}): zero-strength rule {r.label} in fired_rules")
    done(problems)


def test_07_aggregate_firing_matches_independent_strengths_scholarship():
    """Domain B: rule.aggregate_firing[sim] and fired_rules match independent_strengths within 1e-6 across all types."""
    problems: list[str] = []
    loads = [0.0, 6.0, 7.5, 8.0, 9.0, 15.0, 18.0]

    for stype, t in config.SCHOLARSHIP_THRESHOLDS.items():
        sys_b, rules_b = scholarship.build_system(stype)
        cgpas = sorted({0.0, round(t - 0.33, 2), round(t - 0.15, 2), round(t - 0.01, 2), t, round(t + 0.01, 2), 4.0})
        for hours in loads:
            for cgpa in cgpas:
                sim = ctrl.ControlSystemSimulation(sys_b)
                sim.input["cgpa"] = cgpa
                sim.input["credit_load"] = hours
                sim.compute()

                inputs = {"cgpa": cgpa, "credit_load": hours}
                ind = explain.independent_strengths(inputs, rules_b)
                fired = {f.rule_id: f.strength for f in call_fired_rules(sim, rules_b, scholarship.RULE_REFS)}

                for r in rules_b:
                    agg_val = float(r.aggregate_firing[sim])
                    ind_val = float(ind[r.label])
                    orc_val = oracle_rule_strength(r, inputs)
                    if abs(agg_val - ind_val) > 1e-6 or abs(ind_val - orc_val) > 1e-6:
                        problems.append(
                            f"scholarship[{stype}](cgpa={cgpa}, load={hours}) rule {r.label}: "
                            f"aggregate_firing={agg_val:.6f}, independent={ind_val:.6f}, oracle={orc_val:.6f}"
                        )
                    if agg_val > 1e-9 and abs(fired.get(r.label, -1.0) - agg_val) > 1e-6:
                        problems.append(
                            f"scholarship[{stype}](cgpa={cgpa}, load={hours}) rule {r.label}: "
                            f"fired_rules={fired.get(r.label)} != {agg_val:.6f}"
                        )
    done(problems)


def test_08_independent_strengths_is_pure_membership_oracle():
    """independent_strengths works on fresh rules without any ControlSystemSimulation and handles AND/OR trees."""
    problems: list[str] = []
    cgpa = variables.cgpa_antecedent(2.0)
    pcount = variables.probation_count_antecedent()
    risk = variables.risk_consequent()

    # Build synthetic rules that have never been attached to a ControlSystemSimulation
    r_and = ctrl.Rule(cgpa["borderline"] & pcount["first"], risk["high"], label="T_AND")
    r_or = ctrl.Rule(cgpa["below_min"] | pcount["second"], risk["critical"], label="T_OR")
    inputs = {"cgpa": 1.89, "probation_count": 1}

    try:
        out = explain.independent_strengths(inputs, [r_and, r_or])
        want_and = min(
            float(fuzz.interp_membership(cgpa.universe, cgpa["borderline"].mf, 1.89)),
            float(fuzz.interp_membership(pcount.universe, pcount["first"].mf, 1)),
        )
        want_or = max(
            float(fuzz.interp_membership(cgpa.universe, cgpa["below_min"].mf, 1.89)),
            float(fuzz.interp_membership(pcount.universe, pcount["second"].mf, 1)),
        )
        if abs(out["T_AND"] - want_and) > 1e-6:
            problems.append(f"independent_strengths AND: got {out['T_AND']:.6f}, expected {want_and:.6f}")
        if abs(out["T_OR"] - want_or) > 1e-6:
            problems.append(f"independent_strengths OR: got {out['T_OR']:.6f}, expected {want_or:.6f}")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"independent_strengths failed on unsimulated rules: {type(exc).__name__}: {exc}")
    done(problems)


# ========================================== 9-10 advice.py ==================
def test_09_risk_label_membership_peaks_and_severity_tie_breaking():
    """risk_label picks highest-membership term and breaks exact ties toward the more severe term."""
    problems: list[str] = []
    cases = [
        (0.0, "low"),
        (10.0, "low"),
        (16.4, "low"),
        (16.5, "moderate"),   # exact 0.5 / 0.5 tie between low [0,0,33] and moderate [0,33,67] -> more severe
        (33.0, "moderate"),
        (49.9, "moderate"),
        (50.0, "high"),       # exact 0.5 / 0.5 tie between moderate [0,33,67] and high [33,67,100] -> more severe
        (67.0, "high"),
        (83.4, "high"),
        (83.5, "critical"),   # exact 0.5 / 0.5 tie between high [33,67,100] and critical [67,100,100] -> more severe
        (100.0, "critical"),
    ]
    for score, want in cases:
        got = advice.risk_label(score)
        if got != want:
            problems.append(f"risk_label({score}) = {got!r}, expected {want!r}")

    prev_sev = -1
    for score in np.linspace(0.0, 100.0, 201):
        lbl = advice.risk_label(float(score))
        if lbl not in SEVERITY:
            problems.append(f"risk_label({score}) returned invalid term {lbl!r}")
            break
        if SEVERITY[lbl] < prev_sev:
            problems.append(f"risk_label severity decreased at score={score}: got {lbl!r}")
            break
        prev_sev = SEVERITY[lbl]
    done(problems)


def test_10_compose_advice_verdict_first_clause_and_risk_sentence():
    """Advice always states the official verdict first (with its handbook clause), then the fuzzy risk sentence."""
    problems: list[str] = []
    scenarios = [
        ("probation", crisp_rules.probation_verdict(2.50, 0), "low", {"cgpa": 2.50, "probation_count": 0}),
        ("probation", crisp_rules.probation_verdict(1.99, 0), "moderate", {"cgpa": 1.99, "probation_count": 0}),
        ("probation", crisp_rules.probation_verdict(1.80, 1), "critical", {"cgpa": 1.80, "probation_count": 1}),
        ("probation", crisp_rules.probation_verdict(1.50, 2), "critical", {"cgpa": 1.50, "probation_count": 2}),
        (
            "scholarship",
            crisp_rules.scholarship_verdict(3.80, "merit_batch_topper"),
            "low",
            {"cgpa": 3.80, "scholarship_type": "merit_batch_topper", "credit_hours": 15.0},
        ),
        (
            "scholarship",
            crisp_rules.scholarship_verdict(3.40, "advance_merit_continuation"),
            "high",
            {"cgpa": 3.40, "scholarship_type": "advance_merit_continuation", "credit_hours": 15.0},
        ),
    ]
    for dom, v, r_label, inp in scenarios:
        text = call_compose_advice(dom, v, r_label, inp)
        if not isinstance(text, str) or not text.strip():
            problems.append(f"compose_advice({dom}, {v.code}, {r_label}) returned empty advice")
            continue
        low_text = text.lower()
        verdict_tokens = [v.label.lower(), v.code.lower(), v.code.replace("_", " ").lower()]
        v_positions = [low_text.find(tok) for tok in verdict_tokens if low_text.find(tok) != -1]
        if not v_positions:
            problems.append(f"compose_advice({v.code}): official verdict label/code not found in {text!r}")
            continue
        v_pos = min(v_positions)

        clause_nums = [c.lstrip("§").strip() for c in v.clauses]
        c_positions = [low_text.find(cn.lower()) for cn in clause_nums if low_text.find(cn.lower()) != -1]
        if not c_positions:
            problems.append(f"compose_advice({v.code}): none of clauses {v.clauses} cited in {text!r}")
            continue

        r_pos = low_text.find(r_label.lower())
        if r_pos == -1:
            problems.append(f"compose_advice({v.code}, {r_label}): risk label {r_label!r} not found in {text!r}")
            continue
        if v_pos > r_pos:
            problems.append(
                f"compose_advice({v.code}, {r_label}): official verdict must appear BEFORE fuzzy risk in {text!r}"
            )
    done(problems)


# ========================================== 11-12 engine.py =================
def test_11_engine_evaluate_validation_gate_and_domain_routing():
    """FuzzyAdvisor.evaluate validates all inputs first and raises InputError (never clamps or leaks skfuzzy errors)."""
    problems: list[str] = []
    adv = engine.FuzzyAdvisor()

    bad_calls: list[tuple[str, dict[str, Any]]] = [
        ("unknown_domain", {"cgpa": 3.0, "probation_count": 0}),
        ("", {"cgpa": 3.0, "probation_count": 0}),
        ("probation", {"cgpa": -0.01, "probation_count": 0}),
        ("probation", {"cgpa": 4.01, "probation_count": 0}),
        ("probation", {"cgpa": "2,5", "probation_count": 0}),
        ("probation", {"cgpa": "nan", "probation_count": 0}),
        ("probation", {"cgpa": 2.5, "probation_count": 3}),
        ("probation", {"cgpa": 2.5, "probation_count": 1.5}),
        ("probation", {"cgpa": 2.5, "probation_count": None}),
        ("scholarship", {"cgpa": 3.5, "scholarship_type": "invalid_type", "credit_hours": 15}),
        ("scholarship", {"cgpa": 3.5, "scholarship_type": "merit_batch_topper", "credit_hours": -1}),
        ("scholarship", {"cgpa": 3.5, "scholarship_type": "merit_batch_topper", "credit_hours": 19}),
        ("scholarship", {"cgpa": 4.5, "scholarship_type": "merit_batch_topper", "credit_hours": 15}),
    ]
    for dom, kwargs in bad_calls:
        try:
            if dom == "scholarship":
                eval_scholarship(adv, kwargs["cgpa"], kwargs["scholarship_type"], kwargs["credit_hours"])
            else:
                adv.evaluate(dom, **kwargs)
            problems.append(f"evaluate({dom!r}, {kwargs}) succeeded but must raise InputError")
        except validation.InputError:
            pass
        except Exception as exc:  # noqa: BLE001
            problems.append(f"evaluate({dom!r}, {kwargs}) raised {type(exc).__name__} ({exc}), expected InputError")
    done(problems)


def test_12_engine_evaluate_fresh_simulation_and_result_structure():
    """FuzzyAdvisor.evaluate returns a complete AdvisorResult and uses a fresh simulation per evaluation."""
    problems: list[str] = []
    adv = engine.FuzzyAdvisor()

    res_a1 = adv.evaluate("probation", cgpa=" 1.99 ", probation_count="0")
    res_b1 = eval_scholarship(adv, " 3.74 ", "merit_batch_topper", "15")
    res_a2 = adv.evaluate("probation", cgpa=3.90, probation_count=2)
    res_a1_repeat = adv.evaluate("probation", cgpa=1.99, probation_count=0)
    res_b1_repeat = eval_scholarship(engine.FuzzyAdvisor(), 3.74, "merit_batch_topper", 15.0)

    for tag, res, dom in (("probation", res_a1, "probation"), ("scholarship", res_b1, "scholarship")):
        if not isinstance(res, models.AdvisorResult):
            problems.append(f"{tag}: evaluate did not return AdvisorResult")
            continue
        if res.domain != dom:
            problems.append(f"{tag}: result.domain is {res.domain!r}, expected {dom!r}")
        if not isinstance(res.risk_score, float) or not (0.0 <= res.risk_score <= 100.0):
            problems.append(f"{tag}: risk_score {res.risk_score!r} must be a float in [0, 100]")
        if res.risk_label != advice.risk_label(res.risk_score):
            problems.append(
                f"{tag}: risk_label {res.risk_label!r} != advice.risk_label({res.risk_score}) "
                f"({advice.risk_label(res.risk_score)!r})"
            )
        if not res.fired_rules or not all(isinstance(r, models.FiredRule) for r in res.fired_rules):
            problems.append(f"{tag}: result.fired_rules must be a non-empty list[FiredRule]")

    if abs(res_a1.risk_score - res_a1_repeat.risk_score) > 1e-9 or res_a1.fired_rules != res_a1_repeat.fired_rules:
        problems.append("probation evaluation mutated shared simulation state across calls")
    if abs(res_b1.risk_score - res_b1_repeat.risk_score) > 1e-9 or res_b1.fired_rules != res_b1_repeat.fired_rules:
        problems.append("scholarship evaluation did not match a fresh FuzzyAdvisor instance")
    if abs(res_a2.risk_score - res_a1.risk_score) < 1.0:
        problems.append("distinct probation queries returned nearly identical risk scores")
    done(problems)


# ========================================== 13-16 invariants I1, I2, I3 =====
def test_13_invariant_I1_verdict_always_matches_crisp_rules():
    """I1: FuzzyAdvisor verdict always equals crisp_rules output; fuzzy layer never overrides official verdict."""
    problems: list[str] = []
    adv = engine.FuzzyAdvisor()
    cgpas = [0.0, 1.67, 1.99, 2.00, 2.01, 2.49, 2.50, 2.51, 3.49, 3.50, 3.51, 3.74, 3.75, 3.76, 4.00]

    for count in config.PROBATION_COUNTS:
        for cgpa in cgpas:
            got = adv.evaluate("probation", cgpa=cgpa, probation_count=count).verdict
            want = crisp_rules.probation_verdict(cgpa, count)
            if got != want:
                problems.append(f"I1 probation(cgpa={cgpa}, count={count}): got {got}, expected {want}")

    for stype in TYPES:
        for hours in (6.0, 9.0, 15.0):
            for cgpa in cgpas:
                got = eval_scholarship(adv, cgpa, stype, hours).verdict
                want = crisp_rules.scholarship_verdict(cgpa, stype)
                if got != want:
                    problems.append(
                        f"I1 scholarship[{stype}](cgpa={cgpa}, hours={hours}): got {got}, expected {want}"
                    )
    done(problems)


def test_14_invariant_I2_probation_risk_label_monotonic_with_cgpa():
    """I2 (Domain A): risk_label never becomes less severe as CGPA falls, for every probation_count."""
    problems: list[str] = []
    adv = engine.FuzzyAdvisor()
    cgpas_desc = sorted(
        {round(x, 2) for x in np.arange(0.0, 4.01, 0.05)} | {1.67, 1.90, 1.99, 2.00, 2.01, 2.33},
        reverse=True,
    )

    for count in config.PROBATION_COUNTS:
        prev_cgpa = cgpas_desc[0]
        prev_label = adv.evaluate("probation", cgpa=prev_cgpa, probation_count=count).risk_label
        for cgpa in cgpas_desc[1:]:
            cur_label = adv.evaluate("probation", cgpa=cgpa, probation_count=count).risk_label
            if SEVERITY[cur_label] < SEVERITY[prev_label]:
                problems.append(
                    f"I2 violated in probation(count={count}): CGPA fell from {prev_cgpa} ({prev_label}) "
                    f"to {cgpa} ({cur_label})"
                )
                break
            prev_cgpa, prev_label = cgpa, cur_label
    done(problems)


def test_15_invariant_I2_scholarship_risk_label_monotonic_with_cgpa_and_load():
    """I2 (Domain B): risk_label never becomes less severe as CGPA falls (or as credit load drops)."""
    problems: list[str] = []
    adv = engine.FuzzyAdvisor()
    cgpas_desc = sorted(
        {round(x, 2) for x in np.arange(0.0, 4.01, 0.10)}
        | {2.17, 2.49, 2.50, 2.51, 2.83, 3.17, 3.49, 3.50, 3.51, 3.74, 3.75, 3.76},
        reverse=True,
    )

    for stype in TYPES:
        for hours in (6.0, 7.5, 9.0, 15.0):
            prev_cgpa = cgpas_desc[0]
            prev_label = eval_scholarship(adv, prev_cgpa, stype, hours).risk_label
            for cgpa in cgpas_desc[1:]:
                cur_label = eval_scholarship(adv, cgpa, stype, hours).risk_label
                if SEVERITY[cur_label] < SEVERITY[prev_label]:
                    problems.append(
                        f"I2 violated in scholarship[{stype}](hours={hours}): "
                        f"CGPA fell from {prev_cgpa} ({prev_label}) to {cgpa} ({cur_label})"
                    )
                    break
                prev_cgpa, prev_label = cgpa, cur_label

        for cgpa in (2.50, 3.50, 3.75, 4.00):
            reg_label = eval_scholarship(adv, cgpa, stype, 15.0).risk_label
            under_label = eval_scholarship(adv, cgpa, stype, 6.0).risk_label
            if SEVERITY[under_label] < SEVERITY[reg_label]:
                problems.append(
                    f"scholarship[{stype}] at CGPA={cgpa}: under-load (6h -> {under_label}) "
                    f"was less severe than regular load (15h -> {reg_label})"
                )
    done(problems)


def test_16_invariant_I3_adverse_verdict_implies_at_least_moderate_risk():
    """I3: Whenever verdict is worse than GOOD_STANDING / ELIGIBLE, risk_label is at least 'moderate'."""
    problems: list[str] = []
    adv = engine.FuzzyAdvisor()
    cgpas = sorted({round(x, 2) for x in np.arange(0.0, 4.01, 0.05)} | {1.99, 2.49, 3.49, 3.74})

    for count in config.PROBATION_COUNTS:
        for cgpa in cgpas:
            res = adv.evaluate("probation", cgpa=cgpa, probation_count=count)
            if res.verdict.code != "GOOD_STANDING" and SEVERITY[res.risk_label] < SEVERITY["moderate"]:
                problems.append(
                    f"I3 violated in probation(cgpa={cgpa}, count={count}): "
                    f"verdict={res.verdict.code} but risk_label={res.risk_label!r}"
                )

    for stype in TYPES:
        for hours in (6.0, 9.0, 15.0):
            for cgpa in cgpas:
                res = eval_scholarship(adv, cgpa, stype, hours)
                if res.verdict.code != "ELIGIBLE" and SEVERITY[res.risk_label] < SEVERITY["moderate"]:
                    problems.append(
                        f"I3 violated in scholarship[{stype}](cgpa={cgpa}, hours={hours}): "
                        f"verdict={res.verdict.code} but risk_label={res.risk_label!r}"
                    )
    done(problems)


# ========================================== 17-18 boundary tables ===========
def test_17_design_section7_boundary_table_probation_count_zero():
    """DESIGN.md §7 boundary table for T=2.00, probation_count=0 matches official verdicts and risk bands."""
    problems: list[str] = []
    adv = engine.FuzzyAdvisor()
    table = [
        (1.50, "PROBATION_1", "high"),
        (1.67, "PROBATION_1", "high"),
        (1.99, "PROBATION_1", "moderate"),
        (2.00, "GOOD_STANDING", "moderate"),
        (2.01, "GOOD_STANDING", "moderate"),
        (2.33, "GOOD_STANDING", "low"),
        (3.00, "GOOD_STANDING", "low"),
        (4.00, "GOOD_STANDING", "low"),
    ]
    for cgpa, want_verdict, want_risk in table:
        res = adv.evaluate("probation", cgpa=cgpa, probation_count=0)
        if res.verdict.code != want_verdict or res.risk_label != want_risk:
            problems.append(
                f"DESIGN §7 boundary CGPA={cgpa} (count=0): got ({res.verdict.code}, {res.risk_label!r}, "
                f"score={res.risk_score:.2f}), expected ({want_verdict}, {want_risk!r})"
            )

    # Also verify severe boundary behaviour for probation_count=1 and 2 at CGPA=1.99 / 2.00
    for count, want_199_verdict, want_risk in ((1, "PROBATION_2", "high"), (2, "DROP", "critical")):
        r_below = adv.evaluate("probation", cgpa=1.99, probation_count=count)
        r_at = adv.evaluate("probation", cgpa=2.00, probation_count=count)
        if r_below.verdict.code != want_199_verdict or SEVERITY[r_below.risk_label] < SEVERITY[want_risk]:
            problems.append(
                f"probation(cgpa=1.99, count={count}): got ({r_below.verdict.code}, {r_below.risk_label}), "
                f"expected ({want_199_verdict}, >={want_risk})"
            )
        if r_at.verdict.code != "GOOD_STANDING" or r_at.risk_label != want_risk:
            problems.append(
                f"probation(cgpa=2.00, count={count}): got ({r_at.verdict.code}, {r_at.risk_label}), "
                f"expected (GOOD_STANDING, {want_risk})"
            )
    done(problems)


def test_18_scholarship_threshold_boundaries_and_credit_load_sensitivity():
    """Domain B boundaries at T-0.33, T-0.01, T, T+0.01, 4.00 and under-load penalty at 6 credit hours."""
    problems: list[str] = []
    adv = engine.FuzzyAdvisor()

    for stype, t in config.SCHOLARSHIP_THRESHOLDS.items():
        cases = [
            (round(t - config.GRADE_STEP, 2), 15.0, "SUSPENDED", "high"),
            (round(t - 0.01, 2), 15.0, "SUSPENDED", "moderate"),
            (t, 15.0, "ELIGIBLE", "moderate"),
            (round(t + 0.01, 2), 15.0, "ELIGIBLE", "moderate"),
            (4.00, 15.0, "ELIGIBLE", "low"),
            (4.00, 6.0, "ELIGIBLE", "moderate"),  # B4: safe CGPA but under_load -> moderate risk
            (t, 6.0, "ELIGIBLE", "high"),         # B5: borderline CGPA and under_load -> high risk
        ]
        for cgpa, hours, want_verdict, want_risk in cases:
            res = eval_scholarship(adv, cgpa, stype, hours)
            if res.verdict.code != want_verdict or res.risk_label != want_risk:
                problems.append(
                    f"scholarship[{stype}](cgpa={cgpa}, hours={hours}): got ({res.verdict.code}, "
                    f"{res.risk_label!r}, score={res.risk_score:.2f}), expected ({want_verdict}, {want_risk!r})"
                )
    done(problems)