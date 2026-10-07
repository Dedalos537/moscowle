"""Sincronización en vivo de la configuración.

Cada escritura de configuración incrementa la versión de su ámbito. Las pantallas abiertas consultan
`/api/live/versions` (barato) y, si la versión cambió —por otro admin, otra pestaña o el propio bot—, recargan solas.
Va en la base de datos: sirve igual con varios procesos y no depende de websockets.
"""

import logging

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.system_setting import LiveVersion

logger = logging.getLogger('app.live_sync')


def bump(scope):
    """Incrementa la versión del ámbito (lo crea si no existe). Nunca rompe la operación que lo invoca."""
    try:
        row = db.session.get(LiveVersion, scope)
        if row is None:
            db.session.add(LiveVersion(scope=scope, version=1))
            try:
                db.session.commit()
                return 1
            except IntegrityError:
                db.session.rollback()
                row = db.session.get(LiveVersion, scope)
        row.version = (row.version or 0) + 1
        db.session.commit()
        return row.version
    except Exception:
        db.session.rollback()
        logger.exception('No se pudo actualizar la versión de %s', scope)
        return None


def versions(scopes):
    rows = LiveVersion.query.filter(LiveVersion.scope.in_(list(scopes))).all() if scopes else []
    found = {r.scope: r.version for r in rows}
    return {s: found.get(s, 0) for s in scopes}
