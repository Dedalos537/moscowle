from app.models import SessionMetrics, db
from sqlalchemy import func

class MetricsRepository:
    @staticmethod
    def get_global_avg_accuracy():
        return db.session.query(func.avg(SessionMetrics.accurracy)).scalar() or 0

    @staticmethod
    def get_avg_accuracy_by_therapist(therapist_id):
        from app.models import User
        return db.session.query(func.avg(SessionMetrics.accurracy))\
            .join(User, SessionMetrics.user_id == User.id)\
            .filter(User.role == 'jugador', User.assigned_therapist_id == therapist_id).scalar() or 0

    @staticmethod
    def get_avg_accuracy_by_therapist_date_range(therapist_id, start_date, end_date=None):
        from app.models import User
        query = db.session.query(func.avg(SessionMetrics.accurracy))\
            .join(User, SessionMetrics.user_id == User.id)\
            .filter(SessionMetrics.date >= start_date, User.assigned_therapist_id == therapist_id)
        
        if end_date:
            query = query.filter(SessionMetrics.date < end_date)
            
        return query.scalar()

    @staticmethod
    def get_recent_metrics_by_user(user_id, limit=10):
        return SessionMetrics.query.filter_by(user_id=user_id).order_by(SessionMetrics.date.desc()).limit(limit).all()

    @staticmethod
    def count_sessions_by_user(user_id):
        return SessionMetrics.query.filter_by(user_id=user_id).count()

    @staticmethod
    def get_avg_accuracy_by_user(user_id):
        return db.session.query(func.avg(SessionMetrics.accurracy)).filter_by(user_id=user_id).scalar() or 0

    @staticmethod
    def get_avg_time_by_user(user_id):
        return db.session.query(func.avg(SessionMetrics.avg_time)).filter_by(user_id=user_id).scalar() or 0

    @staticmethod
    def get_last_played_date(user_id):
        return db.session.query(func.max(SessionMetrics.date)).filter_by(user_id=user_id).scalar()

    @staticmethod
    def get_game_stats_by_user(user_id):
        return db.session.query(
            SessionMetrics.game_name,
            func.count(SessionMetrics.id).label('plays'),
            func.avg(SessionMetrics.accurracy).label('avg_acc'),
            func.avg(SessionMetrics.avg_time).label('avg_time')
        ).filter_by(user_id=user_id).group_by(SessionMetrics.game_name).all()
