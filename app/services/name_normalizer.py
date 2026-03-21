import re


CURRENCY_PREFIXES = ["USD ", "KRW ", "JPY ", "EUR "]


def normalize_security_name(raw_name: str) -> str:
    if not raw_name:
        return ""

    text = raw_name.strip()

    for prefix in CURRENCY_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break

    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text
