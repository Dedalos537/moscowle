from typing import List

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.dao.base import BaseDAO
from app.models import User


class UserDAO(BaseDAO[User]):
    async def get_by_email(self, email: str) -> User | None:
        try:
            result = await self.session.execute(select(User).where(User.email == email))
            return result.scalars().first()
        except Exception as e:
            self.logger.error(f'Error fetching user by email {email}: {e}')
            raise

    async def get_active_therapists(self, skip: int = 0, limit: int = 50) -> List[User]:

        try:
            stmt = (
                select(User)
                .where(User.role == 'terapista')
                .where(User.is_active)
                .offset(skip)
                .limit(limit)
                .options(selectinload(User.assigned_sedes))
            )
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f'Error fetching active therapists: {e}')
            raise

    async def get_patients_by_sede(self, sede_id: int, skip: int = 0, limit: int = 50) -> List[User]:
        try:
            stmt = select(User).where(User.role == 'jugador').where(User.sede_id == sede_id).offset(skip).limit(limit)
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f'Error fetching patients for sede {sede_id}: {e}')
            raise
