from datetime import datetime

def get_current_time_str() -> str:
    """Returns local time: e.g., '12:43 PM'"""
    return datetime.now().strftime("%I:%M %p").lstrip('0')

def get_current_date_str() -> str:
    """Returns local date: e.g., 'Tuesday, April 14th, 2026'"""
    now = datetime.now()
    day = now.day
    # Add ordinal suffix
    if 4 <= day <= 20 or 24 <= day <= 30:
        suffix = "th"
    else:
        suffix = ["st", "nd", "rd"][day % 10 - 1]
    
    return now.strftime(f"%A, %B {day}{suffix}, %Y")

def get_current_datetime_str() -> str:
    """Returns combined datetime."""
    return f"It's {get_current_time_str()} on {get_current_date_str()}."

def resolve_temporal_query(query: str) -> str:
    """Main resolver for date/time strings."""
    q = query.lower()
    if "time" in q and "date" in q:
        return get_current_datetime_str()
    if "time" in q:
        return f"It's {get_current_time_str()}."
    if "date" in q or "day" in q or "year" in q or "month" in q:
        return f"Today is {get_current_date_str()}."
    
    return get_current_datetime_str()
