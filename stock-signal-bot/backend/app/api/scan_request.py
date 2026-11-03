import re


SYMBOL_PATTERN = re.compile(r"[A-Z0-9._&-]{1,24}")


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.upper()
    if not SYMBOL_PATTERN.fullmatch(normalized):
        raise ValueError("A valid NSE trading symbol is required.")
    return normalized
