from typing import Generic, TypeVar, Optional, Type
from flask import abort
from app.extensions import db

T = TypeVar('T')


class BaseRepository(Generic[T]):
    def __init__(self, model_class: Type[T]):
        self.model = model_class

    def get_by_id(self, id_val: int) -> Optional[T]:
        return self.model.query.get(id_val)

    def get_by_id_or_404(self, id_val: int) -> T:
        record = self.get_by_id(id_val)
        if not record:
            abort(404, description=f'{self.model.__name__} not found')
        return record

    def list_all(self, **filters) -> list[T]:
        q = self.model.query
        for attr, value in filters.items():
            if value is not None:
                col = getattr(self.model, attr, None)
                if col is not None:
                    q = q.filter(col == value)
        return q.all()

    def paginate(self, page=1, per_page=20, **filters):
        q = self.model.query
        for attr, value in filters.items():
            if value is not None:
                col = getattr(self.model, attr, None)
                if col is not None:
                    q = q.filter(col == value)
        return q.order_by(self.model.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

    def create(self, **kwargs) -> T:
        record = self.model(**kwargs)
        db.session.add(record)
        db.session.commit()
        return record

    def update(self, record: T, **kwargs) -> T:
        for key, value in kwargs.items():
            setattr(record, key, value)
        db.session.commit()
        return record

    def delete(self, record: T) -> None:
        db.session.delete(record)
        db.session.commit()
