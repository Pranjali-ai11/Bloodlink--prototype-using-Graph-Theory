"""Shared donor age and post-donation eligibility rules."""

from calendar import monthrange
from datetime import date


MINIMUM_DONOR_AGE = 18
DONATION_WAITING_MONTHS = 3


def add_calendar_months(value, months):
    """Add calendar months, clamping to the last valid day of the target month."""
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def is_donor_eligible(donor, today=None):
    """Return eligibility, a user-facing reason, and the next eligible date."""
    today = today or date.today()
    age = getattr(getattr(donor, "user", None), "age", None)

    if age is None:
        return {
            "eligible": False,
            "status": "age_required",
            "reason": "Age is required to confirm donor eligibility.",
            "eligible_after": None,
        }

    if age < MINIMUM_DONOR_AGE:
        return {
            "eligible": False,
            "status": "underage",
            "reason": "Donors must be 18 or older to donate.",
            "eligible_after": None,
        }

    last_donation = getattr(donor, "last_donation_date", None)
    if last_donation is None:
        return {
            "eligible": True,
            "status": "eligible",
            "reason": "Eligible to Donate.",
            "eligible_after": None,
        }

    eligible_after = add_calendar_months(last_donation, DONATION_WAITING_MONTHS)
    if today >= eligible_after:
        return {
            "eligible": True,
            "status": "eligible",
            "reason": "Eligible to Donate.",
            "eligible_after": eligible_after,
        }

    return {
        "eligible": False,
        "status": "waiting_period",
        "reason": f"You can donate again on {eligible_after.isoformat()}.",
        "eligible_after": eligible_after,
    }
