from datetime import datetime, timezone
from typing import Optional

def calculate_urgency(deadline_at: Optional[datetime]) -> bool:
    if deadline_at is None:
        return False
    now = datetime.now(timezone.utc)
    if deadline_at.tzinfo is None:
        deadline_at = deadline_at.replace(tzinfo=timezone.utc)
    days_until_deadline = (deadline_at - now).days
    return days_until_deadline <= 3

def calculate_days_until_deadline(deadline_at: Optional[datetime]) -> Optional[int]:
    if deadline_at is None:
        return None
    now = datetime.now(timezone.utc)
    if deadline_at.tzinfo is None:
        deadline_at = deadline_at.replace(tzinfo=timezone.utc)
    return (deadline_at - now).days

def determine_quadrant(is_important: bool, is_urgent: bool) -> str:
    if is_important and is_urgent:
        return "Q1"
    elif is_important and not is_urgent:
        return "Q2"
    elif not is_important and is_urgent:
        return "Q3"
    else:
        return "Q4"