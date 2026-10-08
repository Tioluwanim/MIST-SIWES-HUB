import re
from typing import Any

PHONE = re.compile(r"^0[789][01]\d{8}$")


def normalise_phone(value: Any) -> str | None:
    """Normalise Nigerian mobile numbers (Excel often drops the leading 0 or stores them as numbers).
    Returns None for empty input and raises ValueError for anything that is not a valid number."""
    if value in (None, ""):
        return None
    digits = re.sub(r"\D", "", str(int(value)) if isinstance(value, (int, float)) else str(value))
    if digits.startswith("234") and len(digits) == 13:
        digits = "0" + digits[3:]
    if len(digits) == 10 and digits[0] in "789":
        digits = "0" + digits
    if not PHONE.match(digits):
        raise ValueError("Enter a valid Nigerian mobile number, e.g. 08012345678")
    return digits
