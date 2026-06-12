import os

from flask import Flask

from app.bootstrap import (
    init_extensions,
    init_scheduler_and_ollama,
    init_security,
    init_sentry,
    init_swagger,
    init_template_filters,
    register_auth_loader,
    register_blueprints,
    register_error_handlers,
)
from app.cli import register_cli_commands
from app.logging_setup import setup_logging
from app.middleware.request_handlers import register_request_handlers
from config import Config, ProductionConfig


def create_app(config_class=None):
    if config_class is None:
        env = os.environ.get('FLASK_ENV', 'development')
        is_railway = (
            os.environ.get('RAILWAY_ENVIRONMENT') is not None
            or os.environ.get('RAILWAY_SERVICE_NAME') is not None
            or os.environ.get('RAILWAY_REPLICA_ID') is not None
            or os.environ.get('RAILWAY_GIT_COMMIT_SHA') is not None
        )
        if env == 'production' or is_railway:
            config_class = ProductionConfig
        else:
            config_class = Config

    app = Flask(__name__)
    app.config.from_object(config_class)

    setup_logging(app)
    init_swagger(app)
    init_sentry(app)
    init_security(app)
    init_extensions(app)
    register_auth_loader(app)
    register_error_handlers(app)
    register_request_handlers(app)

    from app.extensions import db

    @app.shell_context_processor
    def make_shell_context():
        return {'db': db, 'User': __import__('app.models', fromlist=['User']).User}

    with app.app_context():
        uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        if uri:
            try:
                from sqlalchemy.engine.url import make_url

                url = make_url(uri)
                app.logger.info(f'DB host={url.host}, user={url.username}')
            except Exception:
                app.logger.info('DB configured URI')

        from app import models as _all_models  # noqa: F401

        try:
            db.create_all()
            app.logger.info('Database tables created/verified')
        except Exception as e:
            app.logger.warning(f'Database tables creation failed (non-fatal): {e}')

        try:
            from flask_migrate import upgrade as migrate_upgrade

            migrate_upgrade()
            app.logger.info('Pending migrations applied')
        except Exception as e:
            app.logger.warning(f'Migration skipped (non-fatal): {e}')

        try:
            _sync_missing_columns(db)
            app.logger.info('Schema sync completed')
        except Exception as e:
            app.logger.warning(f'Schema sync skipped (non-fatal): {e}')

        db.session.remove()

    register_blueprints(app)
    register_cli_commands(app)
    init_template_filters(app)
    init_scheduler_and_ollama(app)

    app.logger.info('Application initialization complete')
    return app


def _sync_missing_columns(db):
    from sqlalchemy import inspect, text

    engine = db.engine
    inspector = inspect(engine)
    dialect = engine.dialect.name

    table_columns = {
        'user': {
            'created_by_id': 'INTEGER',
            'updated_at': 'TIMESTAMP',
            'mfa_enabled': 'BOOLEAN',
            'otp_secret': 'VARCHAR(32)',
            'mfa_failed_attempts': 'INTEGER',
            'mfa_locked_until': 'TIMESTAMP',
        },
        'sede': {
            'is_active': 'BOOLEAN',
            'created_by_id': 'INTEGER',
            'updated_at': 'TIMESTAMP',
        },
        'notification': {
            'created_by_id': 'INTEGER',
            'updated_at': 'TIMESTAMP',
            'is_active': 'BOOLEAN',
        },
    }

    for table, columns in table_columns.items():
        try:
            existing = {c['name'] for c in inspector.get_columns(table)}
        except Exception:
            continue

        for col_name, col_type in columns.items():
            if col_name in existing:
                continue
            try:
                if dialect == 'postgresql':
                    engine.execute(text(f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS {col_name} {col_type}'))
                elif dialect == 'sqlite':
                    stype = (
                        col_type.replace('VARCHAR', 'VARCHAR')
                        .replace('INTEGER', 'INTEGER')
                        .replace('BOOLEAN', 'BOOLEAN')
                        .replace('TIMESTAMP', 'DATETIME')
                    )
                    engine.execute(text(f'ALTER TABLE "{table}" ADD COLUMN {col_name} {stype}'))
                else:
                    engine.execute(text(f'ALTER TABLE {table} ADD COLUMN {col_name} {col_type}'))
            except Exception:
                pass
