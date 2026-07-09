"""Phone validation for the Ethiopian market."""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# E.164 Ethiopian mobile: +251, then 9 (Ethio Telecom) or 7 (Safaricom ET),
# then exactly 8 more digits — e.g. +251911223344 / +251712345678.
ET_MOBILE_RE = re.compile(r"^\+251[79]\d{8}$")


def validate_ethiopian_phone(value):
    """Accept only valid Ethiopian mobile numbers.

    Works on PhoneNumber objects (already normalized to E.164 by the field)
    and on raw strings like 0911223344 / 251911223344 / +251911223344.
    """
    raw = str(value).strip().replace(" ", "")
    # Normalize common local forms to E.164.
    if raw.startswith("00251"):
        raw = "+" + raw[2:]
    elif raw.startswith("251") and not raw.startswith("+"):
        raw = "+" + raw
    elif raw.startswith("0") and len(raw) == 10:
        raw = "+251" + raw[1:]

    if not ET_MOBILE_RE.match(raw):
        raise ValidationError(
            _(
                "Enter a valid Ethiopian mobile number: +251 followed by 9 or 7 "
                "and 8 more digits (e.g. +251911223344 or 0911223344)."
            ),
            code="invalid_ethiopian_phone",
        )
