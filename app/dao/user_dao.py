from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models import User
from app.dao.base import BaseDAO
import logging

class UserDAO(BaseDAO[User]):
    """
    Specific Data Access implementation for User entity.
    Includes custom queries optimized for specific business needs.
    """
    
    async def get_by_email(self, email: str) -> Optional[User]:
        try:
            result = await self.session.execute(
                select(User).where(User.email == email)
            )
            return result.scalars().first()
        except Exception as e:
            self.logger.error(f"Error fetching user by email {email}: {e}")
            raise

    async def get_active_therapists(self, skip: int = 0, limit: int = 50) -> List[User]:
        """
        Optimized query to fetch only active therapists.
        Uses selectinload to fetch related 'assigned_sedes' if needed, otherwise defer.
        """
        try:
            stmt = (
                select(User)
                .where(User.role == 'terapista')
                .where(User.is_active == True)
                .offset(skip)
                .limit(limit)
                .options(selectinload(User.assigned_sedes)) # Eager load for performance
            )
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error fetching active therapists: {e}")
            raise

    async def get_patients_by_sede(self, sede_id: int, skip: int = 0, limit: int = 50) -> List[User]:
        """Fetch patients filtered by Sede ID efficiently."""
        try:
            stmt = (
                select(User)
                .where(User.role == 'jugador')
                .where(User.sede_id == sede_id)
                .offset(skip)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error fetching patients for sede {sede_id}: {e}")
            raise
