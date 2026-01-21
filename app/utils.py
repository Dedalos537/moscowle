from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:
    # Fallback minimal implementation if zoneinfo missing (unlikely on Python 3.9+)
    class ZoneInfo:
        def __init__(self, key):
             pass
    ZoneInfoNotFoundError = Exception

def get_user_timezone(user):
    """Helper to get a ZoneInfo object from user."""
    if not user or not user.timezone:
        return timezone.utc
    try:
        return ZoneInfo(user.timezone)
    except (ZoneInfoNotFoundError, Exception):
        return timezone.utc

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
    start_utc = local_start.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = local_end.astimezone(timezone.utc).replace(tzinfo=None)
    
    return start_utc, end_utc

def normalize_datetime_for_storage(dt_input, user_timezone_str='UTC'):
    """
    Convert any datetime (string, aware, or naive) to UTC naive for DB storage.
    
    Args:
        dt_input: Can be datetime object or ISO string
        user_timezone_str: Timezone string (e.g., 'America/Bogota', 'UTC')
    
    Returns:
        datetime: Naive UTC datetime ready for DB storage
    """
    # If it's a string, parse it
    if isinstance(dt_input, str):
        # Handle Z suffix for UTC
        if dt_input.endswith('Z'):
            dt_input = dt_input[:-1] + '+00:00'
        try:
            dt = datetime.fromisoformat(dt_input)
        except ValueError:
            # Try without microseconds
            dt = datetime.fromisoformat(dt_input.split('.')[0])
    else:
        dt = dt_input
    
    try:
        user_tz = ZoneInfo(user_timezone_str)
    except:
        user_tz = timezone.utc
    
    # If naive, assume it's in user's local time
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=user_tz)
    
    # Convert to UTC and make naive
    return dt.astimezone(timezone.utc).replace(tzinfo=None)

def localize_datetime_for_display(dt_utc_naive, user_timezone_str='UTC'):
    """
    Convert UTC naive datetime from DB to user's local timezone.
    
    Args:
        dt_utc_naive: Naive datetime assumed to be in UTC
        user_timezone_str: Target timezone string
    
    Returns:
        datetime: Timezone-aware datetime in user's timezone
    """
    if dt_utc_naive is None:
        return None
    
    try:
        user_tz = ZoneInfo(user_timezone_str)
    except:
        user_tz = timezone.utc
    
    # Make it aware as UTC first
    dt_utc_aware = dt_utc_naive.replace(tzinfo=timezone.utc)
    
    # Convert to user's timezone
    return dt_utc_aware.astimezone(user_tz)
