from celery import Celery

celery_app = Celery('moscowle')

def init_celery(app):
    celery_app.conf.update(
        broker_url=app.config.get('CELERY_BROKER_URL', 'redis://redis:6379/0'),
        result_backend=app.config.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0'),
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone=app.config.get('TIMEZONE', 'America/Lima'),
        enable_utc=True,
    )

    class ContextTask(celery_app.Task):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask
    return celery_app
