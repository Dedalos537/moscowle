from datetime import datetime
from typing import List

from sqlalchemy import or_
from sqlalchemy.future import select

from app.dao.base import BaseDAO
from app.models import Appointment


class AppointmentDAO(BaseDAO[Appointment]):
    async def get_upcoming_for_user(self, user_id: int, role: str = 'terapista', limit: int = 10) -> List[Appointment]:
        now = datetime.utcnow()
        if role == 'terapista':
            condition = Appointment.therapist_id == user_id
        elif role == 'jugador':
            condition = Appointment.patient_id == user_id
        else:
            condition = or_(Appointment.therapist_id == user_id, Appointment.patient_id == user_id)

        query = (
            select(Appointment)
            .where(condition, Appointment.start_time > now, Appointment.is_active)
            .order_by(Appointment.start_time.asc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
