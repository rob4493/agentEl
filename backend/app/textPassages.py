import re

def splitPassages(text: str) -> list[str]:
    # A period within a version or decimal is not a sentence boundary.
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]
