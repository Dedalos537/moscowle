from datetime import date, datetime

from app.extensions import db
from app.models import Holiday

NATIONAL_HOLIDAYS_2026 = {
    '2026-01-01': 'Año Nuevo',
    '2026-04-02': 'Jueves Santo',
    '2026-04-03': 'Viernes Santo',
    '2026-05-01': 'Día del Trabajo',
    '2026-06-29': 'San Pedro y San Pablo',
    '2026-07-28': 'Fiestas Patrias',
    '2026-07-29': 'Fiestas Patrias',
    '2026-08-06': 'Batalla de Junín',
    '2026-08-30': 'Santa Rosa de Lima',
    '2026-10-08': 'Combate de Angamos',
    '2026-11-01': 'Día de Todos los Santos',
    '2026-12-08': 'Inmaculada Concepción',
    '2026-12-09': 'Batalla de Ayacucho',
    '2026-12-25': 'Navidad',
}

REGIONAL_HOLIDAYS_2026 = {
    'PIURA': {
        '2026-08-15': 'Aniversario de San Miguel de Piura',
    },
}


def _parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def is_holiday(value, region='PIURA'):
    d = _parse_date(value)
    key = d.strftime('%Y-%m-%d')

    if key in NATIONAL_HOLIDAYS_2026:
        return True

    if region:
        regional = REGIONAL_HOLIDAYS_2026.get(region.upper(), {})
        if key in regional:
            return True

    try:
        row = Holiday.query.filter(
            Holiday.date == d,
            Holiday.is_active.is_(True),
            (Holiday.region.is_(None)) | (Holiday.region == region),
        ).first()
        return row is not None
    except Exception:
        return False


def get_holidays(region='PIURA'):
    seen = {}
    for key, name in NATIONAL_HOLIDAYS_2026.items():
        seen[key] = {'date': key, 'name': name, 'holiday_type': 'nacional', 'region': None}

    if region:
        for key, name in REGIONAL_HOLIDAYS_2026.get(region.upper(), {}).items():
            seen[key] = {'date': key, 'name': name, 'holiday_type': 'regional', 'region': region.upper()}

    try:
        for row in Holiday.query.filter(Holiday.is_active.is_(True)).all():
            key = row.date.strftime('%Y-%m-%d')
            if row.region and region and row.region.upper() != region.upper():
                continue
            seen[key] = {
                'date': key,
                'name': row.name,
                'holiday_type': row.holiday_type,
                'region': row.region,
            }
    except Exception:
        pass

    return [seen[key] for key in sorted(seen)]


def seed_holidays():
    created = 0
    try:
        for key, name in NATIONAL_HOLIDAYS_2026.items():
            d = date.fromisoformat(key)
            exists = Holiday.query.filter(Holiday.date == d, Holiday.region.is_(None)).first()
            if not exists:
                db.session.add(Holiday(date=d, name=name, holiday_type='nacional', region=None))
                created += 1
        for region, holidays in REGIONAL_HOLIDAYS_2026.items():
            for key, name in holidays.items():
                d = date.fromisoformat(key)
                exists = Holiday.query.filter(Holiday.date == d, Holiday.region == region).first()
                if not exists:
                    db.session.add(Holiday(date=d, name=name, holiday_type='regional', region=region))
                    created += 1
        db.session.commit()
    except Exception:
        db.session.rollback()
        return 0
    return created
