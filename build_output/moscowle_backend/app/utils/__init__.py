from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import db

DEFAULT_TIMEZONE = 'America/Lima'

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:
    # Fallback minimal implementation if zoneinfo missing (unlikely on Python 3.9+)
    class ZoneInfo:
        def __init__(self, key):
             pass
    ZoneInfoNotFoundError = Exception

def handle_db_errors(f):
    """
    Decorator para manejar errores de base de datos y liberar conexiones
    Debe usarse en métodos de servicios que acceden a DB
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            db.session.commit()
            return result
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(
                f"Database error in {f.__name__}",
                exc_info=True,
                extra={'function': f.__name__}
            )
            # Re-raise to let caller handle if needed, or return None/Error
            raise
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error in {f.__name__}",
                exc_info=True,
                extra={'function': f.__name__}
            )
            raise
        finally:
            # Always close the session to prevent leaks
            # Note: With SQLALCHEMY_COMMIT_ON_TEARDOWN=True this might be redundant but safe
            if db.session:    
                db.session.close() # Only if using scoped_session manually or need instant return to pool
    
    return decorated_function

def get_user_timezone(user):
    """Helper to get a ZoneInfo object from user. Falls back to DEFAULT_TIMEZONE (America/Lima)."""
    if not user or not user.timezone:
        return ZoneInfo(DEFAULT_TIMEZONE)
    try:
        return ZoneInfo(user.timezone)
    except (ZoneInfoNotFoundError, Exception):
        return ZoneInfo(DEFAULT_TIMEZONE)

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

def normalize_datetime_for_storage(dt_input, user_timezone_str=DEFAULT_TIMEZONE):
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

def localize_datetime_for_display(dt_utc_naive, user_timezone_str=DEFAULT_TIMEZONE):
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
        if dt_utc_naive.tzinfo is None:
             dt_utc_naive = dt_utc_naive.replace(tzinfo=timezone.utc)
        return dt_utc_naive.astimezone(user_tz)
    except:
        return dt_utc_naive
