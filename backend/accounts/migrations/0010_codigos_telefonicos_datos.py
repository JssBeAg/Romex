"""
Data for the phone codes:
1. Loads the catalog of countries and dialing codes (accounts/phone_codes_data.py).
2. Converts the phones that already exist: until now the whole number was one free-text
   field ("844 123 4567", "+52 844..."). Each one becomes country code + digits only.
   - With a "+" the longest matching code wins ("+1 844..." -> +1).
   - Without it, México (+52) is assumed (the system was used in Mexico), and a leading
     52 / 521 is dropped when the rest still looks like a full number (10 digits).
"""

import re

from django.db import migrations

from accounts.phone_codes_data import PHONE_CODES


def load_codes(apps, schema_editor):
    PhoneCode = apps.get_model("accounts", "PhoneCode")
    PhoneCode.objects.bulk_create(
        PhoneCode(iso=iso, country_name=name, code=code, is_active=active)
        for iso, name, code, active in PHONE_CODES
    )


def split_phone(raw, codes):
    """Returns (code, digits) for an old free-text phone. `codes` is the set of known codes."""
    digits = re.sub(r"\D", "", raw)
    if raw.strip().startswith("+"):
        for size in (3, 2, 1):
            if digits[:size] in codes and len(digits) - size >= 4:
                return digits[:size], digits[size:]
    code = "52"
    if len(digits) > 10 and digits.startswith("521") and len(digits) - 3 >= 10:
        digits = digits[3:]
    elif len(digits) > 10 and digits.startswith("52"):
        digits = digits[2:]
    return code, digits


def convert_phones(apps, schema_editor):
    PhoneCode = apps.get_model("accounts", "PhoneCode")
    User = apps.get_model("accounts", "User")
    by_code = {}
    for phone_code in PhoneCode.objects.order_by("-is_active", "pk"):
        by_code.setdefault(phone_code.code, phone_code)
    # "+52" must exist for the default; "+1" resolves to the United States (first active)
    mexico = PhoneCode.objects.get(iso="MX")
    by_code["52"] = mexico
    by_code["1"] = PhoneCode.objects.get(iso="US")
    for user in User.objects.exclude(phone_number=""):
        code, digits = split_phone(user.phone_number, set(by_code))
        digits = digits[-14:]  # the new column holds at most 14 digits
        user.phone_code = by_code[code]
        user.phone_number = digits
        user.save(update_fields=["phone_code", "phone_number"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_codigos_y_contactos"),
    ]

    operations = [
        migrations.RunPython(load_codes, migrations.RunPython.noop),
        # Reverse: the number keeps only its digits (the old field accepted that)
        migrations.RunPython(convert_phones, migrations.RunPython.noop),
    ]
