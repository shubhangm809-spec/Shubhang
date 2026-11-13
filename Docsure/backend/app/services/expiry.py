
from datetime import date, datetime

def get_expiry_details(expiry_date):
    if not expiry_date:
        return None

    if isinstance(expiry_date, str):
        expiry_date = date.fromisoformat(expiry_date[:10])

    elif isinstance(expiry_date, datetime):
        expiry_date = expiry_date.date()

    today = date.today()
    remaining_days = (expiry_date - today).days

    if remaining_days < 0:
        status = "Expired"
    elif remaining_days == 0:
        status = "Expires Today"
    elif remaining_days <= 7:
        status = "Critical"
    elif remaining_days <= 30:
        status = "Expiring Soon"
    else:
        status = "Active"

    return {
        "remaining_days": remaining_days,
        "status": status
    }
