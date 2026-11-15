import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

from src import config


def cgpa_antecedent(threshold: float) -> ctrl.Antecedent:
    # Build the CGPA antecedent variable with terms anchored at threshold T.
    universe = np.round(
        np.arange(
            config.CGPA_MIN,
            config.CGPA_MAX + config.CGPA_RESOLUTION / 2,
            config.CGPA_RESOLUTION,
        ),
        2,
    )
    var = ctrl.Antecedent(universe, "cgpa")

    w = config.GRADE_STEP
    w_up = min(w, config.CGPA_MAX - threshold)

    var["below_min"] = fuzz.trapmf(universe, [0.0, 0.0, threshold - w, threshold])
    var["borderline"] = fuzz.trimf(universe, [threshold - w, threshold, threshold + w_up])
    var["safe"] = fuzz.trapmf(
        universe, [threshold, threshold + w_up, config.CGPA_MAX, config.CGPA_MAX + 1e-9]
    )

    return var

def probation_count_antecedent() -> ctrl.Antecedent:
    # Build the probation_count antecedent variable on {0, 1, 2}.
    universe = np.array(config.PROBATION_COUNTS, dtype=int)
    var = ctrl.Antecedent(universe, "probation_count")

    var["none"] = fuzz.trimf(universe, [0, 0, 1])
    var["first"] = fuzz.trimf(universe, [0, 1, 2])
    var["second"] = fuzz.trimf(universe, [1, 2, 2])

    return var


def credit_load_antecedent() -> ctrl.Antecedent:
    # Build the credit_load antecedent variable on [0, 18], step 0.5.
    universe = np.round(
        np.arange(
            0.0,
            config.CREDITS_MAX + config.CREDIT_RESOLUTION / 2,
            config.CREDIT_RESOLUTION,
        ),
        2,
    )
    var = ctrl.Antecedent(universe, "credit_load")

    var["under_load"] = fuzz.trapmf(universe, [0.0, 0.0, 6.0, 9.0])
    var["regular"] = fuzz.trapmf(
        universe, [6.0, 9.0, float(config.CREDITS_MAX), float(config.CREDITS_MAX) + 1e-9]
    )

    return var


def risk_consequent() -> ctrl.Consequent:
    # Build the risk consequent variable on [0, 100], step 1.
    universe = np.arange(
        config.RISK_UNIVERSE[0],
        config.RISK_UNIVERSE[1] + config.RISK_RESOLUTION,
        config.RISK_RESOLUTION,
    )
    var = ctrl.Consequent(universe, "risk")

    var["low"] = fuzz.trimf(universe, [0, 0, 33])
    var["moderate"] = fuzz.trimf(universe, [0, 33, 67])
    var["high"] = fuzz.trimf(universe, [33, 67, 100])
    var["critical"] = fuzz.trimf(universe, [67, 100, 100])

    return var
