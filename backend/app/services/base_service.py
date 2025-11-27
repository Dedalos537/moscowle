from contextlib import contextmanager
from flask import current_app
from ..extensions import db


class BaseService:
    """Base service providing transaction helper and common patterns."""

    @contextmanager
    def transaction(self):
        try:
            yield
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Transaction failed")
            raise
