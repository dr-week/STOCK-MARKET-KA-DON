import math


VALID_OUTCOMES = {"WIN", "LOSS", "BREAKEVEN"}


def normalize_outcome(outcome: str) -> str:
    normalized = outcome.upper()
    if normalized not in VALID_OUTCOMES:
        raise ValueError(f"outcome must be one of {VALID_OUTCOMES}, got {normalized!r}")
    return normalized


def validate_exit(actual_exit: float) -> None:
    if not math.isfinite(actual_exit) or actual_exit <= 0:
        raise ValueError("actual_exit must be finite and greater than zero")
