import os
import json
from datetime import datetime
from app.extensions import db
from sqlalchemy import inspect, text

def run_backup():
    try:
        backup_dir = os.environ.get('BACKUP_DIR', 'backups')
        os.makedirs(backup_dir, exist_ok=True)
    except Exception:
        return None

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f'db_backup_{timestamp}.json'
    filepath = os.path.join(backup_dir, filename)

    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()
    allowed_tables = set(table_names)

    backup_data = {
        'generated_at': timestamp,
        'version': '1.0',
        'tables': {}
    }

    for table_name in table_names:
        if table_name.startswith('alembic_'):
            continue
        if table_name not in allowed_tables:
            continue

        try:
            result = db.session.execute(text(f'SELECT * FROM `{table_name}`'))
            rows = []
            for row in result.mappings().all():
                cleaned = {}
                for key, value in dict(row).items():
                    if isinstance(value, datetime):
                        cleaned[key] = value.isoformat()
                    elif isinstance(value, bytes):
                        cleaned[key] = value.hex()
                    elif isinstance(value, (__import__('decimal').Decimal,)):
                        cleaned[key] = float(value)
                    elif hasattr(value, 'isoformat'):
                        cleaned[key] = value.isoformat()
                    else:
                        cleaned[key] = value
                rows.append(cleaned)

            backup_data['tables'][table_name] = {
                'row_count': len(rows),
                'rows': rows
            }
        except Exception as e:
            backup_data['tables'][table_name] = {
                'error': str(e),
                'row_count': 0,
                'rows': []
            }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)

    _cleanup_old_backups(backup_dir, keep=7)

    return filepath


def _cleanup_old_backups(backup_dir, keep=7):
    try:
        files = sorted([
            f for f in os.listdir(backup_dir)
            if f.startswith('db_backup_') and f.endswith('.json')
        ])
        for f in files[:-keep] if len(files) > keep else []:
            os.remove(os.path.join(backup_dir, f))
    except Exception:
        pass
