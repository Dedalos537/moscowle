from typing import Type, Any, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func


class BaseRepository:
    """Generic repository providing common CRUD operations for SQLAlchemy models.

    Usage:
        repo = BaseRepository(Model, db.session)
        repo.get(1)
    """

    def __init__(self, model: Type, session: Session):
        self.model = model
        self.session = session

    def get(self, id_: Any):
        return self.session.get(self.model, id_)

    def filter_by(self, **kwargs):
        return self.session.query(self.model).filter_by(**kwargs)

    def find_one(self, **kwargs):
        return self.filter_by(**kwargs).first()

    def list(self, offset: int = 0, limit: int = 50):
        q = self.session.query(self.model)
        return q.offset(offset).limit(limit).all()

    def count(self) -> int:
        return self.session.query(func.count(self.model.id)).scalar()

    def create(self, **kwargs):
        obj = self.model(**kwargs)
        self.session.add(obj)
        return obj

    def update(self, obj, **kwargs):
        for k, v in kwargs.items():
            setattr(obj, k, v)
        return obj

    def delete(self, obj):
        self.session.delete(obj)
