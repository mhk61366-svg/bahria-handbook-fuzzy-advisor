"""Input validation for student advisor queries.

Raises InputError with a student-readable message. Never clamps or guesses.
"""
import math
from typing import Any

from src import config


class InputError(ValueError):
    """Raised when user input violates validation policy."""
    pass


def parse_float(raw: Any, field_name: str = "Input") -> float:
    """Parse a float from numeric or string input.

    Rejects None, empty string/whitespace, booleans, nan, inf, and strings with decimal commas.
    """
    if raw is None:
        raise InputError(f"{field_name} cannot be empty.")
    if isinstance(raw, bool):
        raise InputError(f"{field_name} must be a number, not a boolean.")
    if isinstance(raw, str):
        val_str = raw.strip()
        if not val_str:
            raise InputError(f"{field_name} cannot be empty.")
        if "," in val_str:
            raise InputError(f"{field_name} uses a decimal comma; please use a dot (e.g. 2.5).")
        try:
            val = float(val_str)
        except ValueError as err:
            raise InputError(f"{field_name} must be a valid number, got {raw!r}.") from err
    elif isinstance(raw, (int, float)):
        val = float(raw)
    else:
        raise InputError(f"{field_name} must be a valid number, got {raw!r}.")

    if math.isnan(val) or math.isinf(val):
        raise InputError(f"{field_name} must be a finite number, got {val}.")

    return val


def validate_cgpa(raw: Any) -> float:
    """Validate CGPA to be a float between config.CGPA_MIN and config.CGPA_MAX."""
    val = parse_float(raw, field_name="CGPA")
    if val < config.CGPA_MIN or val > config.CGPA_MAX:
        raise InputError(
            f"CGPA must be between {config.CGPA_MIN:.2f} and {config.CGPA_MAX:.2f}, got {val}."
        )
    return val


def validate_probation_count(raw: Any) -> int:
    """Validate probation count to be an integer in config.PROBATION_COUNTS."""
    if raw is None:
        raise InputError("Probation count cannot be empty.")
    if isinstance(raw, bool):
        raise InputError("Probation count must be an integer, not a boolean.")
    if isinstance(raw, str):
        val_str = raw.strip()
        if not val_str:
            raise InputError("Probation count cannot be empty.")
        if "," in val_str:
            raise InputError("Probation count must be an integer.")
        try:
            val_f = float(val_str)
        except ValueError as err:
            raise InputError(f"Probation count must be an integer, got {raw!r}.") from err
        if not val_f.is_integer():
            raise InputError(f"Probation count must be an integer, got {raw!r}.")
        val = int(val_f)
    elif isinstance(raw, int):
        val = raw
    elif isinstance(raw, float):
        if not raw.is_integer():
            raise InputError(f"Probation count must be an integer, got {raw}.")
        val = int(raw)
    else:
        raise InputError(f"Probation count must be an integer, got {raw!r}.")

    if val not in config.PROBATION_COUNTS:
        raise InputError(
            f"Probation count must be one of {config.PROBATION_COUNTS}, got {val}."
        )
    return val


def validate_credit_hours(raw: Any) -> float:
    """Validate credit hours to be a number between 0 and config.CREDITS_MAX."""
    val = parse_float(raw, field_name="Credit hours")
    if val < 0.0 or val > config.CREDITS_MAX:
        raise InputError(
            f"Credit hours must be between 0 and {config.CREDITS_MAX}, got {val}."
        )
    return val


def validate_scholarship_type(raw: Any) -> str:
    """Validate scholarship type to be a recognized key in config.SCHOLARSHIP_THRESHOLDS."""
    if not isinstance(raw, str) or raw not in config.SCHOLARSHIP_THRESHOLDS:
        allowed = ", ".join(repr(k) for k in config.SCHOLARSHIP_THRESHOLDS)
        raise InputError(
            f"Unknown scholarship type {raw!r}. Allowed types: {allowed}."
        )
    return raw
