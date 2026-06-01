from typing import List, Optional
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from app.models import Appointment, User
from app.dao.base import BaseDAO

class AppointmentDAO(BaseDAO[Appointment]):
    
    async def get_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime, 
        therapist_id: Optional[int] = None,
        patient_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Appointment]:
        try:
            query = (
                select(Appointment)
                .where(Appointment.start_time >= start_date)
                .where(Appointment.start_time <= end_date)
                .options(
                    selectinload(Appointment.therapist),
                    selectinload(Appointment.patient)
                )
                .order_by(Appointment.start_time.asc())
                .offset(skip)
                .limit(limit)
            )
            
            if therapist_id:
                query = query.where(Appointment.therapist_id == therapist_id)
            if patient_id:
                query = query.where(Appointment.patient_id == patient_id)
                
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error fetching appointments by range: {e}")
            raise

    async def get_upcoming_for_user(self, user_id: int, role: str, limit: int = 5) -> List[Appointment]:
        try:
            now = datetime.utcnow()
            query = (
                select(Appointment)
                .where(Appointment.start_time >= now)
                .where(Appointment.status != 'cancelled')
                .order_by(Appointment.start_time.asc())
                .limit(limit)
            )
            
            if role == 'terapista':
                query = query.where(Appointment.therapist_id == user_id)
            else:
                query = query.where(Appointment.patient_id == user_id)

            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
             self.logger.error(f"Error fetching upcoming appointments for user {user_id}: {e}")
             raise
