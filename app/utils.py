from datetime import datetime, timedelta
import pytz

def get_user_timezone(user):
    """Helper to get a pytz timezone object from user."""
    if not user or not user.timezone:
        return pytz.UTC
    try:
        return pytz.timezone(user.timezone)
    except pytz.UnknownTimeZoneError:
        return pytz.UTC

def get_user_now(user):
    """
    Returns the current datetime for the user based on their timezone.
    Returns a timezone-aware datetime.
    """
    tz = get_user_timezone(user)
    return datetime.now(tz)

def get_user_today_utc_range(user):
    """
    Returns the start and end of the user's current day, converted to UTC.
    Useful for querying the database (which stores UTC) for records belonging to the user's 'today'.
    
    Returns: (start_utc_naive, end_utc_naive)
    """
    tz = get_user_timezone(user)
    user_now = datetime.now(tz)
    
    # Start of day in user's local time
    local_start = user_now.replace(hour=0, minute=0, second=0, microsecond=0)
    # End of day in user's local time
    local_end = local_start + timedelta(days=1)
    
    # Convert to UTC
    start_utc = local_start.astimezone(pytz.UTC).replace(tzinfo=None)
    end_utc = local_end.astimezone(pytz.UTC).replace(tzinfo=None)
    
    return start_utc, end_utc
