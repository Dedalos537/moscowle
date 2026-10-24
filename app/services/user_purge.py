"""Borrado definitivo de un usuario sin romper llaves foráneas.

Antes se borraban a mano solo mensajes, sesiones, métricas y pagos; cualquier otra fila que apuntara al usuario
(contrato y cuotas, juegos de la sesión, grupos, solicitudes, avisos…) hacía fallar el borrado con un 500.

Aquí se recorren las llaves foráneas del modelo: lo que es *del* usuario (columna obligatoria) se borra, en cascada
con lo que dependa de esas filas; lo que solo lo *menciona* (columna opcional: creado por, revisado por, terapeuta
asignado…) se deja en NULL para no perder el registro.
"""

from sqlalchemy import select

from app.extensions import db

MAX_DEPTH = 6


def _referencing(table):
    """(tabla hija, columna) de cada llave foránea que apunta a `table`."""
    for child in db.metadata.sorted_tables:
        for col in child.columns:
            for fk in col.foreign_keys:
                if fk.column.table is table:
                    yield child, col


def _purge(table, ids, depth=0, seen=None):
    if not ids:
        return
    if depth > MAX_DEPTH:
        raise RuntimeError(f'cadena de dependencias demasiado larga en {table.name}')
    seen = seen if seen is not None else set()
    for child, col in list(_referencing(table)):
        if col.nullable:
            db.session.execute(child.update().where(col.in_(ids)).values({col.name: None}))
            continue
        pk = list(child.primary_key.columns)
        if len(pk) == 1 and (child.name, col.name) not in seen:
            child_ids = [r[0] for r in db.session.execute(select(pk[0]).where(col.in_(ids)))]
            _purge(child, child_ids, depth + 1, seen | {(child.name, col.name)})
        db.session.execute(child.delete().where(col.in_(ids)))


def purge_user(user):
    """Borra al usuario y todo lo suyo. No hace commit: el que llama decide."""
    table = user.__table__
    _purge(table, [user.id])
    db.session.execute(table.delete().where(table.c.id == user.id))
