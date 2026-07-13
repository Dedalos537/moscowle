from datetime import UTC, datetime, timedelta, timezone
from functools import wraps

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db

DEFAULT_TIMEZONE = 'America/Lima'

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:

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
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.error(f'Database error in {f.__name__}', exc_info=True, extra={'function': f.__name__})
            raise
        except Exception:
            db.session.rollback()
            current_app.logger.error(f'Unexpected error in {f.__name__}', exc_info=True, extra={'function': f.__name__})
            raise
        finally:
            if db.session:
                db.session.close()

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


def get_user_day_utc_range(user, date_value):
    """
    Rango UTC (naive) de un día calendario en la zona horaria del usuario.
    date_value: str 'YYYY-MM-DD', date o datetime.
    Returns: (start_utc_naive, end_utc_naive) con fin exclusivo.
    """
    tz = get_user_timezone(user)
    if isinstance(date_value, str):
        d = datetime.strptime(date_value[:10], '%Y-%m-%d').date()
    elif isinstance(date_value, datetime):
        d = date_value.date()
    else:
        d = date_value

    local_start = datetime(d.year, d.month, d.day, tzinfo=tz)
    local_end = local_start + timedelta(days=1)
    start_utc = local_start.astimezone(UTC).replace(tzinfo=None)
    end_utc = local_end.astimezone(UTC).replace(tzinfo=None)
    return start_utc, end_utc


def get_user_today_utc_range(user):
    """
    Returns the start and end of the user's current day, converted to UTC.
    Useful for querying the database (which stores UTC) for records belonging to the user's 'today'.

    Returns: (start_utc_naive, end_utc_naive)
    """
    tz = get_user_timezone(user)
    user_now = datetime.now(tz)

    local_start = user_now.replace(hour=0, minute=0, second=0, microsecond=0)
    local_end = local_start + timedelta(days=1)

    start_utc = local_start.astimezone(UTC).replace(tzinfo=None)
    end_utc = local_end.astimezone(UTC).replace(tzinfo=None)

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
    if isinstance(dt_input, str):
        if dt_input.endswith('Z'):
            dt_input = dt_input[:-1] + '+00:00'
        try:
            dt = datetime.fromisoformat(dt_input)
        except ValueError:
            dt = datetime.fromisoformat(dt_input.split('.')[0])
    else:
        dt = dt_input

    try:
        user_tz = ZoneInfo(user_timezone_str)
    except Exception:
        user_tz = UTC

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=user_tz)

    return dt.astimezone(UTC).replace(tzinfo=None)


def parse_datetime(value):
    """Robust datetime parser. Naive datetimes assumed America/Lima (UTC-5). Returns naive UTC."""
    if not value:
        return None
    try:
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        dt = datetime.fromisoformat(value)
        if dt.tzinfo:
            return dt.astimezone(UTC).replace(tzinfo=None)
        return dt.replace(tzinfo=timezone(timedelta(hours=-5))).astimezone(UTC).replace(tzinfo=None)
    except Exception:
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
            try:
                dt = datetime.strptime(value, fmt)
                return dt.replace(tzinfo=timezone(timedelta(hours=-5))).astimezone(UTC).replace(tzinfo=None)
            except Exception:
                continue
    return None


def localize_datetime_for_display(dt_utc_naive, user_timezone_str=DEFAULT_TIMEZONE):
    """
    Convert UTC naive datetime from DB to user's local timezone.

    Args:
        dt_utc_naive: Naive datetime assumed to be in UTC
        user_timezone_str: Target timezone string (e.g. 'America/Lima') or ZoneInfo object

    Returns:
        datetime: Timezone-aware datetime in user's timezone
    """
    if dt_utc_naive is None:
        return None

    try:
        if isinstance(user_timezone_str, str):
            user_tz = ZoneInfo(user_timezone_str)
        elif hasattr(user_timezone_str, 'key'):
            user_tz = user_timezone_str
        else:
            user_tz = ZoneInfo(str(user_timezone_str))
        if dt_utc_naive.tzinfo is None:
            dt_utc_naive = dt_utc_naive.replace(tzinfo=UTC)
        return dt_utc_naive.astimezone(user_tz)
    except Exception:
        return dt_utc_naive
