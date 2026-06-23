from flask import current_app, has_request_context
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


class RoutingSession(Session):
    _WRITE_KEYWORDS = frozenset({'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER'})

    def get_bind(self, mapper=None, clause=None, **kw):
        if not current_app or not has_request_context():
            return self._primary
        if self.dirty or self.deleted or self.new:
            return self._primary
        if clause is not None:
            compiled = clause.compile()
            stmt = compiled.string.strip().upper()
            if any(stmt.startswith(kw) for kw in self._WRITE_KEYWORDS):
                return self._primary
        return self._replica or self._primary


def init_db_routing(app):
    from app.extensions import db as sqla_db

    primary_url = app.config['SQLALCHEMY_DATABASE_URI']
    replica_url = app.config.get('REPLICA_DATABASE_URL', '')

    primary = create_engine(primary_url, pool_pre_ping=True, pool_size=10)
    replica = create_engine(replica_url, pool_pre_ping=True, pool_size=5) if replica_url else None

    RoutingSession._primary = primary
    RoutingSession._replica = replica

    routing_session = sessionmaker(class_=RoutingSession)
    session = routing_session()

    sqla_db.session = session
    sqla_db.engine = primary

    app.logger.info(
        f'DB routing initialized: primary={primary_url[:30]}... '
        f'replica={replica_url[:30] if replica_url else "none"}...'
    )
