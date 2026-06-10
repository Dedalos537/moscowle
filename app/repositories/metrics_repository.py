from sqlalchemy import func

from app.models import SessionMetrics, User, db


class MetricsRepository:
    @staticmethod
    def get_global_avg_accuracy():
        return db.session.query(func.avg(SessionMetrics.accurracy)).scalar() or 0

    @staticmethod
    def get_avg_accuracy_by_therapist(therapist_id):
        # Use existing relationships or explicit filters to avoid missing column errors
        try:
            res = (
                db.session.query(func.avg(SessionMetrics.accurracy))
                .join(User, SessionMetrics.user_id == User.id)
                .filter(User.role == 'jugador', User.therapists.any(User.id == therapist_id))
                .scalar()
            )
            return res or 0
        except Exception:
            # Fallback for older schema if necessary
            return (
                db.session.query(func.avg(SessionMetrics.accurracy))
                .join(User, SessionMetrics.user_id == User.id)
                .filter(User.role == 'jugador', User.assigned_therapist_id == therapist_id)
                .scalar()
                or 0
            )

    @staticmethod
    def get_avg_accuracy_by_therapist_date_range(therapist_id, start_date, end_date=None):
        try:
            query = (
                db.session.query(func.avg(SessionMetrics.accurracy))
                .join(User, SessionMetrics.user_id == User.id)
                .filter(SessionMetrics.date >= start_date, User.therapists.any(User.id == therapist_id))
            )

            if end_date:
                query = query.filter(SessionMetrics.date < end_date)

            return query.scalar() or 0
        except Exception:
            query = (
                db.session.query(func.avg(SessionMetrics.accurracy))
                .join(User, SessionMetrics.user_id == User.id)
                .filter(SessionMetrics.date >= start_date, User.assigned_therapist_id == therapist_id)
            )

            if end_date:
                query = query.filter(SessionMetrics.date < end_date)

            return query.scalar() or 0

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
        return (
            db.session.query(
                SessionMetrics.game_name,
                func.count(SessionMetrics.id).label('plays'),
                func.avg(SessionMetrics.accurracy).label('avg_acc'),
                func.avg(SessionMetrics.avg_time).label('avg_time'),
            )
            .filter_by(user_id=user_id)
            .group_by(SessionMetrics.game_name)
            .all()
        )

    @staticmethod
    def get_by_user(user_id, limit=20, skip=0):
        return (
            SessionMetrics.query.filter_by(user_id=user_id)
            .order_by(SessionMetrics.date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_average_scores(user_id, game_id=None):
        query = db.session.query(func.avg(SessionMetrics.accurracy)).filter(SessionMetrics.user_id == user_id)
        if game_id:
            query = query.filter(SessionMetrics.game_id == game_id)
        return query.scalar() or 0.0
