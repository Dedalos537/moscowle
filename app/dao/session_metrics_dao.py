from typing import List, Optional
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy import func
from app.models import SessionMetrics, User, Game, Appointment
from app.dao.base import BaseDAO

class SessionMetricsDAO(BaseDAO[SessionMetrics]):

    async def get_by_user(self, user_id: int, limit: int = 50, skip: int = 0) -> List[SessionMetrics]:
        try:
            query = (
                select(SessionMetrics)
                .where(SessionMetrics.user_id == user_id)
                .order_by(SessionMetrics.date.desc())
                # .options(selectinload(SessionMetrics.session)) # Removed — no 'session' relationship defined
                .offset(skip).limit(limit)
            )
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error fetching session metrics for user {user_id}: {e}")
            raise

    async def get_average_scores(self, user_id: int, game_id: Optional[int] = None) -> float:
        try:
            stmt = select(func.avg(SessionMetrics.accurracy).label('avg_accuracy')).where(SessionMetrics.user_id == user_id)
            if game_id:
                stmt = stmt.where(SessionMetrics.game_id == game_id)
            
            result = await self.session.execute(stmt)
            return result.scalar() or 0.0
        except Exception as e:
            self.logger.error(f"Error calculating average score for user {user_id}: {e}")
            raise
