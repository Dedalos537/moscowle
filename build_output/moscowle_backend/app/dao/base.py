from typing import Generic, TypeVar, List, Optional, Type, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, func 
from sqlalchemy.orm import selectinload
from app.extensions import db  # Use existing models base if possible, or define interface
import logging

# Define generic type for Models
T = TypeVar("T")

class BaseDAO(Generic[T]):
    """
    Base Data Access Object implementing generic CRUD operations 
    with high-performance patterns.
    """
    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session
        self.logger = logging.getLogger(f"DAO.{model.__name__}")

    async def get_by_id(self, id: Any) -> Optional[T]:
        """Fetch a single record by ID."""
        try:
            result = await self.session.execute(
                select(self.model).where(self.model.id == id)
            )
            return result.scalars().first()
        except Exception as e:
            self.logger.error(f"Error fetching {self.model.__name__} with id {id}: {e}")
            raise

    async def get_all(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        filters: Optional[Dict] = None,
        load_options: Optional[List] = None
    ) -> List[T]:
        """
        Fetch records with pagination and optional filtering/loading strategies.
        Avoids SELECT * by relying on ORM deferral if customized, or use generic selection.
        """
        try:
            query = select(self.model).offset(skip).limit(limit)
            
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        query = query.where(getattr(self.model, key) == value)

            if load_options:
                for opt in load_options:
                    query = query.options(opt)

            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error fetching list of {self.model.__name__}: {e}")
            raise

    async def create(self, obj_in: Dict[str, Any]) -> T:
        """Create a new record."""
        try:
            db_obj = self.model(**obj_in)
            self.session.add(db_obj)
            await self.session.flush() # Flush to get ID, commit handled by context manager
            return db_obj
        except Exception as e:
            self.logger.error(f"Error creating {self.model.__name__}: {e}")
            raise

    async def update(self, id: Any, obj_in: Dict[str, Any]) -> Optional[T]:
        """Update a record efficiently."""
        try:
            # Check availability first (optional depending on strategy)
            # For update, we can use direct update statement for speed
            stmt = (
                update(self.model)
                .where(self.model.id == id)
                .values(**obj_in)
                .execution_options(synchronize_session="fetch")
            )
            await self.session.execute(stmt)
            return await self.get_by_id(id)
        except Exception as e:
            self.logger.error(f"Error updating {self.model.__name__} with id {id}: {e}")
            raise

    async def delete(self, id: Any) -> bool:
        """Delete a record."""
        try:
            stmt = delete(self.model).where(self.model.id == id)
            result = await self.session.execute(stmt)
            return result.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error deleting {self.model.__name__} with id {id}: {e}")
            raise

    async def count(self, filters: Optional[Dict] = None) -> int:
        """Efficient count query."""
        try:
            query = select(func.count()).select_from(self.model)
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        query = query.where(getattr(self.model, key) == value)
            result = await self.session.execute(query)
            return result.scalar()
        except Exception as e:
            self.logger.error(f"Error counting {self.model.__name__}: {e}")
            raise
