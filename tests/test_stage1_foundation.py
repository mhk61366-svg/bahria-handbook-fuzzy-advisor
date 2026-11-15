from __future__ import annotations

import ast
import dataclasses
import inspect
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import skfuzzy as fuzz
from skfuzzy import control as ctrl

from src import config, crisp_rules, models, validation, variables
from src.domains import probation, scholarship

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
THRESHOLDS = sorted({config.PROBATION_MIN_CGPA, *config.SCHOLARSHIP_THRESHOLDS.values()})
TYPES = list(config.SCHOLARSHIP_THRESHOLDS)


# ----------------------------------------------------------------- helpers --
def done(problems: list[str]) -> None:
    assert not problems, "\n  - " + "\n  - ".join(problems)


def mu(var, term: str, x: float) -> float:
    return float(fuzz.interp_membership(var.universe, var[term].mf, x))


def py_files(folder: Path):
    return sorted(p for p in folder.rglob("*.py") if "__pycache__" not in p.parts)


def check_valid(fn, cases, problems):
    for raw, expected in cases:
        try:
            out = fn(raw)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{fn.__name__}({raw!r}) should be valid but raised {type(exc).__name__}: {exc}")
            continue
        if type(out) is not type(expected) or out != pytest.approx(expected):
            problems.append(f"{fn.__name__}({raw!r}) returned {out!r} ({type(out).__name__}), expected {expected!r}")


def check_invalid(fn, raws, problems):
    for raw in raws:
        try:
            out = fn(raw)
        except validation.InputError as exc:
            if len(str(exc).strip()) < 10:
                problems.append(f"{fn.__name__}({raw!r}): InputError message is too short to help a student")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{fn.__name__}({raw!r}) raised {type(exc).__name__}, must be InputError")
        else:
            problems.append(f"{fn.__name__}({raw!r}) was ACCEPTED (returned {out!r}), must raise InputError")


def top_level_imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


# ============================================================ 1-3 repo state ==
def test_01_repo_cleanup_is_done():
    """YOUR manual cleanup: old folders/files gone, requirements and .gitignore updated."""
    problems = []
    for folder in ("fuzzy_handbook", "docs", "report"):
        if (ROOT / folder).exists():
            problems.append(f"folder '{folder}/' should no longer exist")
    for path in ("data/traceability.csv", "tools/highlight_handbook.py", "tools/build_submission.py"):
        if (ROOT / path).exists():
            problems.append(f"'{path}' was dropped from the design: delete it")
    allowed_tests = re.compile(r"^(conftest|__init__|test_stage\d+_[a-z0-9_]+)\.py$")
    for p in (ROOT / "tests").glob("*.py"):
        if not allowed_tests.match(p.name):
            problems.append(f"tests/{p.name} is not a human-supplied stage test: delete it (agent-written or old stub)")
    req = [ln.strip().lower() for ln in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines() if ln.strip()]
    if "scikit-fuzzy==0.5.0" not in req:
        problems.append("requirements.txt must pin scikit-fuzzy==0.5.0")
    if any("pymupdf" in ln or "fitz" in ln for ln in req):
        problems.append("requirements.txt still lists PyMuPDF")
    ignore = {ln.strip() for ln in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()}
    for entry in ("*.pdf", "test_results.csv", "worked_examples.md"):
        if entry not in ignore:
            problems.append(f".gitignore is missing '{entry}'")
    allowed_top = {
        "src", "data", "tests", "tools", "screenshots", "README.md", "DESIGN.md", "AGENTS.md", "LICENSE",
        "pyproject.toml", "requirements.txt", "requirements-dev.txt", ".gitignore", "test_results.csv",
        "worked_examples.md", ".git", ".venv", ".pytest_cache", "__pycache__", ".idea", ".vscode",
        ".agents", ".agent", ".gemini", "GEMINI.md", ".github", "handbook",
    }
    for p in ROOT.iterdir():
        if p.name not in allowed_top and p.suffix.lower() != ".pdf":
            problems.append(f"unexpected top-level entry '{p.name}'")
    done(problems)


EXPECTED_SRC = {
    "__init__.py", "__main__.py", "config.py", "models.py", "validation.py", "crisp_rules.py",
    "variables.py", "explain.py", "advice.py", "engine.py", "plots.py",
    "domains/__init__.py", "domains/probation.py", "domains/scholarship.py",
    "gui/__init__.py", "gui/app.py", "gui/panels.py",
}
STAGE1_WRITTEN = ["config.py", "models.py", "validation.py", "crisp_rules.py", "variables.py",
                  "domains/probation.py", "domains/scholarship.py"]
ALLOWED_THIRD_PARTY = {"src", "numpy", "scipy", "networkx", "matplotlib", "skfuzzy", "pytest"}


def test_02_source_hygiene():
    """Agent obeyed the project rules: layout, no stub text, no print(), only allowed dependencies."""
    problems = []
    found = {p.relative_to(SRC).as_posix() for p in py_files(SRC)}
    for extra in sorted(found - EXPECTED_SRC):
        problems.append(f"src/{extra} is outside the agreed layout")
    for name in STAGE1_WRITTEN:
        path = SRC / name
        if not path.is_file():
            problems.append(f"src/{name} is missing")
        elif "Contents to write" in path.read_text(encoding="utf-8"):
            problems.append(f"src/{name} still has the scaffold's 'Contents to write' stub text")
    stdlib = set(sys.stdlib_module_names)
    for path in py_files(SRC) + py_files(ROOT / "tools"):
        rel = path.relative_to(ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print" and rel.startswith("src/"):
                problems.append(f"{rel}:{node.lineno} uses print() in library code")
        bad = sorted(m for m in top_level_imports(path) if m not in stdlib and m not in ALLOWED_THIRD_PARTY)
        if bad:
            problems.append(f"{rel} imports disallowed packages: {bad}")
    done(problems)


def test_03_low_level_modules_do_not_load_scikit_fuzzy():
    """Fresh interpreter per module, so indirect imports count too."""
    problems = []
    for module in ("src.config", "src.models", "src.validation", "src.crisp_rules"):
        proc = subprocess.run(
            [sys.executable, "-c", f"import sys, {module}; print('skfuzzy' in sys.modules)"],
            cwd=ROOT, capture_output=True, text=True,
        )
        if proc.returncode != 0:
            problems.append(f"{module} failed to import: {proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else '?'}")
        elif proc.stdout.strip() != "False":
            problems.append(f"{module} loads scikit-fuzzy (directly or indirectly)")
    done(problems)


# ============================================================ 4-5 config, models ==
def test_04_config_handbook_numbers_unchanged():
    problems = []
    if (config.CGPA_MIN, config.CGPA_MAX) != (0.0, 4.0):
        problems.append("CGPA range changed")
    if config.GRADE_STEP != 0.33:
        problems.append(f"GRADE_STEP is {config.GRADE_STEP}, expected 0.33")
    if config.PROBATION_MIN_CGPA != 2.0 or config.DROP_AFTER_PROBATIONS != 2 or tuple(config.PROBATION_COUNTS) != (0, 1, 2):
        problems.append("probation constants changed")
    if config.SCHOLARSHIP_THRESHOLDS != {"merit_batch_topper": 3.75, "advance_merit_continuation": 3.5, "financial_assistance": 2.5}:
        problems.append(f"scholarship thresholds changed: {config.SCHOLARSHIP_THRESHOLDS}")
    if (config.CREDITS_MIN, config.CREDITS_MAX, config.CREDIT_STEP) != (9, 18, 3):
        problems.append("credit constants changed")
    if tuple(config.RISK_TERMS) != ("low", "moderate", "high", "critical") or tuple(config.RISK_UNIVERSE) != (0, 100):
        problems.append("risk terms/universe changed")
    if set(config.SCHOLARSHIP_LABELS) != set(config.SCHOLARSHIP_THRESHOLDS):
        problems.append("SCHOLARSHIP_LABELS keys do not match SCHOLARSHIP_THRESHOLDS")
    if hasattr(config, "RULE_COLORS"):
        problems.append("RULE_COLORS must be removed (it belonged to the dropped highlighting tool)")
    done(problems)


def test_05_models_contract():
    problems = []
    names = lambda cls: [f.name for f in dataclasses.fields(cls)]  # noqa: E731
    if names(models.Verdict) != ["code", "label", "clauses"]:
        problems.append(f"Verdict fields: {names(models.Verdict)}")
    if names(models.FiredRule) != ["rule_id", "text", "strength", "source"]:
        problems.append(f"FiredRule fields: {names(models.FiredRule)}")
    if names(models.AdvisorResult) != ["domain", "inputs", "verdict", "risk_score", "risk_label", "fired_rules", "advice", "warnings"]:
        problems.append(f"AdvisorResult fields: {names(models.AdvisorResult)}")
    for obj in (models.Verdict("X", "x", ("a",)), models.FiredRule("A1", "IF a THEN b", 0.5, "s")):
        try:
            setattr(obj, dataclasses.fields(obj)[0].name, "changed")
            problems.append(f"{type(obj).__name__} must be frozen")
        except dataclasses.FrozenInstanceError:
            pass
    a, b = models.Verdict("X", "x", ("a", "b")), models.Verdict("X", "x", ("a", "b"))
    try:
        if a != b or hash(a) != hash(b):
            problems.append("equal Verdicts must compare equal and hash equal")
    except TypeError:
        problems.append("Verdict must be hashable (a frozen dataclass)")
    try:
        models.AdvisorResult(domain="probation", inputs={}, verdict=a, risk_score=1.0, risk_label="low",
                             fired_rules=[], advice="x", warnings=[])
    except Exception as exc:  # noqa: BLE001
        problems.append(f"AdvisorResult could not be built with all fields: {exc}")
    if not issubclass(models.RuleBaseNotReady, RuntimeError):
        problems.append("RuleBaseNotReady must subclass RuntimeError")
    done(problems)


# ============================================================ 6-9 validation ==
def test_06_validate_cgpa():
    problems = []
    check_valid(validation.validate_cgpa, [(0, 0.0), ("0", 0.0), ("4.00", 4.0), (2.0, 2.0), ("1.99", 1.99),
                                          (" 3.5 ", 3.5), ("\t2.5\n", 2.5), (3, 3.0)], problems)
    check_invalid(validation.validate_cgpa, [-0.01, "-0.1", 4.01, "4.0000001", 5, "abc", "", "   ", "nan", "inf",
                                            "-inf", "2,5", "2.5.1", None, [], float("nan"), float("inf")], problems)
    done(problems)


def test_07_validate_probation_count():
    problems = []
    check_valid(validation.validate_probation_count, [(0, 0), (1, 1), (2, 2), ("0", 0), ("2", 2), (" 1 ", 1)], problems)
    check_invalid(validation.validate_probation_count, [3, -1, 1.5, "1.5", "3", "-1", 2.5, "0.5", "", "abc", None, "nan", []], problems)
    done(problems)


def test_08_validate_credit_hours():
    problems = []
    check_valid(validation.validate_credit_hours, [(0, 0.0), (9, 9.0), ("12", 12.0), (12.5, 12.5), ("18", 18.0), ("7.5", 7.5)], problems)
    check_invalid(validation.validate_credit_hours, [-3, "-0.5", 18.01, 19, "19", "abc", "", None, "nan", "inf", []], problems)
    done(problems)


def test_09_validate_scholarship_type_parse_float_and_error_class():
    problems = []
    if not issubclass(validation.InputError, ValueError):
        problems.append("InputError must subclass ValueError")
    cases = [(k, k) for k in TYPES] + [(f"  {k}\t", k) for k in TYPES]
    check_valid(validation.validate_scholarship_type, cases, problems)
    check_invalid(validation.validate_scholarship_type, ["x", "", "   ", None, "Merit", "merit", "fas", 3, []], problems)
    check_valid(validation.parse_float, [("2.5", 2.5), (" 2.5 ", 2.5), (2, 2.0), ("\t3\n", 3.0), ("-1.25", -1.25)], problems)
    check_invalid(validation.parse_float, ["", "   ", "abc", "nan", "NaN", "inf", "Infinity", "2,5", "1e", None, []], problems)
    done(problems)


# ============================================================ 10-13 crisp rules ==
def test_10_probation_verdict_boundaries():
    problems = []
    below = [0.0, 1.0, 1.5, 1.99, 1.999, math.nextafter(2.0, 0.0)]
    at_or_above = [2.0, math.nextafter(2.0, 5.0), 2.01, 2.5, 3.0, 3.99, 4.0]
    for cgpa in below:
        for count, code in ((0, "PROBATION_1"), (1, "PROBATION_2"), (2, "DROP")):
            got = crisp_rules.probation_verdict(cgpa, count).code
            if got != code:
                problems.append(f"probation_verdict({cgpa!r}, {count}) = {got}, expected {code}")
    for cgpa in at_or_above:
        for count in (0, 1, 2):
            got = crisp_rules.probation_verdict(cgpa, count).code
            if got != "GOOD_STANDING":
                problems.append(f"probation_verdict({cgpa!r}, {count}) = {got}, expected GOOD_STANDING (exactly 2.00 meets the minimum; reaching it resets the count)")
    done(problems)


def test_11_scholarship_verdict_boundaries_and_per_type_thresholds():
    problems = []
    for stype in TYPES:
        t = config.SCHOLARSHIP_THRESHOLDS[stype]
        for cgpa in (t, math.nextafter(t, 5.0), round(t + 0.01, 2), 4.0):
            if crisp_rules.scholarship_verdict(cgpa, stype).code != "ELIGIBLE":
                problems.append(f"{stype}: {cgpa!r} should be ELIGIBLE (threshold {t})")
        for cgpa in (math.nextafter(t, 0.0), round(t - 0.01, 2), 0.0):
            if crisp_rules.scholarship_verdict(cgpa, stype).code != "SUSPENDED":
                problems.append(f"{stype}: {cgpa!r} should be SUSPENDED (threshold {t})")
    table = {
        2.4: ("SUSPENDED", "SUSPENDED", "SUSPENDED"),
        3.0: ("SUSPENDED", "SUSPENDED", "ELIGIBLE"),
        3.6: ("SUSPENDED", "ELIGIBLE", "ELIGIBLE"),
        3.8: ("ELIGIBLE", "ELIGIBLE", "ELIGIBLE"),
    }
    order = ("merit_batch_topper", "advance_merit_continuation", "financial_assistance")
    for cgpa, expected in table.items():
        for stype, code in zip(order, expected):
            got = crisp_rules.scholarship_verdict(cgpa, stype).code
            if got != code:
                problems.append(f"{stype} at CGPA {cgpa}: got {got}, expected {code} (each type has its own threshold)")
    done(problems)


def test_12_crisp_rules_read_config_and_never_round():
    problems = []
    tree = ast.parse((SRC / "crisp_rules.py").read_text(encoding="utf-8"))
    floats = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, float)}
    hard = sorted(floats & {2.0, 2.5, 3.5, 3.75})
    if hard:
        problems.append(f"hardcoded handbook numbers in crisp_rules.py: {hard} (use config.py)")
    if crisp_rules.probation_verdict(1.999, 0).code != "PROBATION_1":
        problems.append("1.999 must be PROBATION_1 (a hidden round(cgpa, 2) flips it to good standing)")
    if crisp_rules.scholarship_verdict(3.7499, "merit_batch_topper").code != "SUSPENDED":
        problems.append("3.7499 must be SUSPENDED for the merit scholarship")
    saved = config.SCHOLARSHIP_THRESHOLDS["financial_assistance"]
    config.SCHOLARSHIP_THRESHOLDS["financial_assistance"] = 3.0
    try:
        if crisp_rules.scholarship_verdict(2.6, "financial_assistance").code != "SUSPENDED":
            problems.append("scholarship threshold is not read from config.SCHOLARSHIP_THRESHOLDS at call time")
    finally:
        config.SCHOLARSHIP_THRESHOLDS["financial_assistance"] = saved
    try:
        crisp_rules.scholarship_verdict(3.0, "nope")
        problems.append("unknown scholarship type must raise")
    except (validation.InputError, KeyError, ValueError):
        pass
    done(problems)


def test_13_verdict_structure_codes_and_clause_citations():
    problems = []

    def cites(verdict, needles):
        return any(n in " | ".join(verdict.clauses) for n in needles)

    probation_cases = [
        (2.0, 0, "GOOD_STANDING", ("5.5.1", "5.5.4")), (1.0, 0, "PROBATION_1", ("5.5.1",)),
        (1.0, 1, "PROBATION_2", ("5.5.1", "5.5.5")), (1.0, 2, "DROP", ("5.5.3",)),
    ]
    labels = set()
    for cgpa, count, code, needles in probation_cases:
        v = crisp_rules.probation_verdict(cgpa, count)
        if not isinstance(v, models.Verdict) or v.code != code:
            problems.append(f"probation_verdict({cgpa}, {count}) is not a Verdict with code {code}")
            continue
        labels.add(v.label)
        if not (isinstance(v.label, str) and v.label.strip()):
            problems.append(f"{code}: empty label")
        if not (isinstance(v.clauses, tuple) and v.clauses and all(isinstance(c, str) and c.strip() for c in v.clauses)):
            problems.append(f"{code}: clauses must be a non-empty tuple of non-empty strings")
        elif not cites(v, needles):
            problems.append(f"{code}: clauses {v.clauses} should cite one of {needles}")
    if len(labels) != 4:
        problems.append("the four probation outcomes need four different labels")
    type_clause = {"merit_batch_topper": ("4.4.3.3",), "advance_merit_continuation": ("4.3.2.2", "4.3.3.1.2"),
                   "financial_assistance": ("4.5.2", "4.5.3")}
    for stype, needles in type_clause.items():
        up, down = crisp_rules.scholarship_verdict(4.0, stype), crisp_rules.scholarship_verdict(0.0, stype)
        if (up.code, down.code) != ("ELIGIBLE", "SUSPENDED") or up.label == down.label:
            problems.append(f"{stype}: ELIGIBLE/SUSPENDED verdicts need distinct codes and labels")
        if not cites(up, needles) or not cites(down, needles):
            problems.append(f"{stype}: verdict must cite its own clause {needles}")
        if not cites(down, ("4.11",)):
            problems.append(f"{stype}: a suspension must cite 4.11")
    done(problems)


# ============================================================ 14-17 membership functions ==
def test_14_cgpa_key_points_for_every_threshold():
    problems = []
    w = config.GRADE_STEP
    for t in THRESHOLDS:
        v, up = variables.cgpa_antecedent(t), min(w, 4.0 - t)

        def trio(x):
            return (mu(v, "below_min", x), mu(v, "borderline", x), mu(v, "safe", x))

        expected = {
            0.0: (1, 0, 0), round(t - w, 2): (1, 0, 0), round(t - w / 2, 3): (0.5, 0.5, 0), t: (0, 1, 0), 4.0: (0, 0, 1),
            round(t - 0.01, 2): (0.01 / w, 1 - 0.01 / w, 0), round(t + 0.01, 2): (0, 1 - 0.01 / up, 0.01 / up),
        }
        for x, want in expected.items():
            got = trio(x)
            if got != pytest.approx(want, abs=0.02 if x == round(t - w / 2, 3) else 1e-6):
                problems.append(f"T={t}: memberships at CGPA {x} are {tuple(round(g, 4) for g in got)}, expected {tuple(round(g, 4) for g in want)}")
    done(problems)


def test_15_cgpa_partition_supports_peak_truncation_and_independence():
    problems = []
    for t in THRESHOLDS:
        v = variables.cgpa_antecedent(t)
        u, below, border, safe = v.universe, v["below_min"].mf, v["borderline"].mf, v["safe"].mf
        if not np.allclose(below + border + safe, 1.0, atol=1e-6):
            problems.append(f"T={t}: the three CGPA terms do not sum to 1 everywhere")
        if not (np.all(below[u >= t - 1e-9] < 1e-9) and np.all(below[u < t - 1e-6] > 0)):
            problems.append(f"T={t}: below_min must be positive for every CGPA < T and exactly 0 from T up")
        if not (np.all(safe[u <= t + 1e-9] < 1e-9) and np.all(safe[u > t + 1e-6] > 0)):
            problems.append(f"T={t}: safe must be 0 up to T and positive above it")
        if abs(u[int(np.argmax(border))] - t) > 0.005 or abs(border.max() - 1.0) > 1e-9:
            problems.append(f"T={t}: borderline must peak at exactly 1.0 at T")
        if abs(mu(v, "safe", 4.0) - 1.0) > 1e-9:
            problems.append(f"T={t}: CGPA 4.00 must be fully safe (is the upper half-width truncated to 4.00 - T?)")
    a, b = variables.cgpa_antecedent(2.0), variables.cgpa_antecedent(3.75)
    again = variables.cgpa_antecedent(2.0)
    if a is b or a is again:
        problems.append("cgpa_antecedent must return a fresh object per call")
    if abs(mu(a, "borderline", 2.0) - 1) > 1e-9 or abs(mu(b, "borderline", 3.75) - 1) > 1e-9 or abs(mu(again, "borderline", 2.0) - 1) > 1e-9:
        problems.append("building one threshold changed another (shared state)")
    done(problems)


def test_16_other_membership_functions():
    problems = []
    pc = variables.probation_count_antecedent()
    for term, hot in (("none", 0), ("first", 1), ("second", 2)):
        for count in (0, 1, 2):
            want = 1.0 if count == hot else 0.0
            if abs(mu(pc, term, count) - want) > 1e-9:
                problems.append(f"probation_count: mu({term}, {count}) should be {want}")
    cl = variables.credit_load_antecedent()
    for hours, under, regular in [(0, 1, 0), (6, 1, 0), (7.5, 0.5, 0.5), (8, 1 / 3, 2 / 3), (9, 0, 1), (13.5, 0, 1), (18, 0, 1)]:
        if (mu(cl, "under_load", hours), mu(cl, "regular", hours)) != pytest.approx((under, regular), abs=1e-6):
            problems.append(f"credit_load at {hours}h: expected under={under:.3f}, regular={regular:.3f}")
    if not np.allclose(cl["under_load"].mf + cl["regular"].mf, 1.0, atol=1e-6):
        problems.append("credit_load terms must sum to 1")
    rk = variables.risk_consequent()
    peaks = {"low": 0, "moderate": 33, "high": 67, "critical": 100}
    for term, peak in peaks.items():
        for other, other_peak in peaks.items():
            want = 1.0 if term == other else 0.0
            if abs(mu(rk, term, other_peak) - want) > 1e-9:
                problems.append(f"risk: mu({term}, {other_peak}) should be {want}")
    if not np.allclose(sum(rk[t].mf for t in config.RISK_TERMS), 1.0, atol=1e-6):
        problems.append("risk terms must sum to 1 over 0-100")
    done(problems)


def test_17_variable_names_terms_and_universes():
    problems = []
    cases = [
        (variables.cgpa_antecedent(2.0), ctrl.Antecedent, "cgpa", {"below_min", "borderline", "safe"}, 401, 0.0, 4.0, 0.01),
        (variables.probation_count_antecedent(), ctrl.Antecedent, "probation_count", {"none", "first", "second"}, 3, 0, 2, 1),
        (variables.credit_load_antecedent(), ctrl.Antecedent, "credit_load", {"under_load", "regular"}, 37, 0, 18, 0.5),
        (variables.risk_consequent(), ctrl.Consequent, "risk", set(config.RISK_TERMS), 101, 0, 100, 1),
    ]
    for var, kind, label, terms, n, lo, hi, step in cases:
        u = var.universe
        if not isinstance(var, kind):
            problems.append(f"{label}: wrong scikit-fuzzy type {type(var).__name__}")
        if var.label != label:
            problems.append(f"variable label is '{var.label}', expected '{label}'")
        if set(var.terms) != terms:
            problems.append(f"{label}: terms are {sorted(var.terms)}, expected {sorted(terms)}")
        if len(u) != n or abs(u[0] - lo) > 1e-12 or abs(u[-1] - hi) > 1e-12 or not np.allclose(np.diff(u), step, atol=1e-9):
            problems.append(f"{label}: universe should run {lo}..{hi} in steps of {step} ({n} points)")
    u = variables.cgpa_antecedent(2.0).universe
    if not np.allclose(u * 100, np.round(u * 100), atol=1e-6):
        problems.append("CGPA universe has float drift (build it from integers)")
    done(problems)


# ============================================================ 18-19 domain files ==
def test_18_domain_files_follow_the_human_owned_block_contract():
    problems = []
    for name in ("probation", "scholarship"):
        text = (SRC / "domains" / f"{name}.py").read_text(encoding="utf-8")
        starts = re.findall(r"^#.*HUMAN-OWNED BLOCK: START", text, re.M)
        ends = re.findall(r"^#.*HUMAN-OWNED BLOCK: END", text, re.M)
        if len(starts) != 1 or len(ends) != 1:
            problems.append(f"{name}.py must contain exactly one START and one END marker comment")
            continue
        s, e = text.index("HUMAN-OWNED BLOCK: START"), text.index("HUMAN-OWNED BLOCK: END")
        if s > e:
            problems.append(f"{name}.py: START marker comes after END marker")
            continue
        inside, outside = text[s:e], text[:s] + text[e:]
        if "def make_rules" not in inside or "def make_rules" in outside:
            problems.append(f"{name}.py: make_rules must be defined inside the human-owned block only")
        if "RULE_REFS" not in inside:
            problems.append(f"{name}.py: RULE_REFS must live inside the human-owned block")
        if "def build_system" not in outside or "def build_system" in inside:
            problems.append(f"{name}.py: build_system must be agent-owned (outside the block)")
    if tuple(inspect.signature(probation.make_rules).parameters) != ("cgpa", "probation_count", "risk"):
        problems.append("probation.make_rules parameters must be (cgpa, probation_count, risk)")
    if tuple(inspect.signature(scholarship.make_rules).parameters) != ("cgpa", "credit_load", "risk"):
        problems.append("scholarship.make_rules parameters must be (cgpa, credit_load, risk)")
    if len(inspect.signature(probation.build_system).parameters) != 0:
        problems.append("probation.build_system() takes no arguments")
    if list(inspect.signature(scholarship.build_system).parameters) != ["scholarship_type"]:
        problems.append("scholarship.build_system must take exactly one parameter: scholarship_type")
    for module in (probation, scholarship):
        if not (isinstance(module.RULE_REFS, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in module.RULE_REFS.items())):
            problems.append(f"{module.__name__}.RULE_REFS must be a dict[str, str]")
    done(problems)


def test_19_build_system_matches_the_rule_base_state():
    """Rule block empty -> RuleBaseNotReady. Rule block filled -> a valid (ControlSystem, rules) pair."""
    problems = []
    jobs = [("probation", "A", lambda: probation.make_rules(variables.cgpa_antecedent(config.PROBATION_MIN_CGPA),
                                                            variables.probation_count_antecedent(), variables.risk_consequent()),
             lambda: probation.build_system())]
    for stype in TYPES:
        jobs.append((f"scholarship[{stype}]", "B",
                     lambda s=stype: scholarship.make_rules(variables.cgpa_antecedent(config.SCHOLARSHIP_THRESHOLDS[s]),
                                                           variables.credit_load_antecedent(), variables.risk_consequent()),
                     lambda s=stype: scholarship.build_system(s)))
    for name, prefix, make, build in jobs:
        rules = make()
        if not isinstance(rules, list):
            problems.append(f"{name}: make_rules must return a list")
            continue
        if not rules:
            try:
                build()
                problems.append(f"{name}: build_system() must raise RuleBaseNotReady while the rule list is empty")
            except models.RuleBaseNotReady as exc:
                if not str(exc).strip():
                    problems.append(f"{name}: RuleBaseNotReady needs a message")
            except Exception as exc:  # noqa: BLE001
                problems.append(f"{name}: raised {type(exc).__name__} instead of RuleBaseNotReady")
        else:
            try:
                system, built = build()
            except Exception as exc:  # noqa: BLE001
                problems.append(f"{name}: build_system() failed with your rules: {type(exc).__name__}: {exc}")
                continue
            labels = [getattr(r, "label", None) for r in built]
            if not isinstance(system, ctrl.ControlSystem) or not all(isinstance(r, ctrl.Rule) for r in built):
                problems.append(f"{name}: build_system must return (ControlSystem, list[Rule])")
            if not all(labels) or len(set(labels)) != len(labels):
                problems.append(f"{name}: every rule needs a unique non-empty label, got {labels}")
            elif not all(re.fullmatch(prefix + r"\d+", lab) for lab in labels):
                problems.append(f"{name}: labels must look like {prefix}1, {prefix}2, ... got {labels}")
    done(problems)