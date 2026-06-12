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
    from flask import current_app
    from sqlalchemy import inspect, text
    from sqlalchemy.types import Boolean, DateTime, Float, Integer, String, Text

    dialect = db.engine.dialect.name
    inspector = inspect(db.engine)
    db_tables = set(inspector.get_table_names())
    app_logger = current_app.logger

    TYPE_MAP = {
        Integer: 'INTEGER',
        int: 'INTEGER',
        String: 'VARCHAR(255)',
        Text: 'TEXT',
        Boolean: 'BOOLEAN',
        bool: 'BOOLEAN',
        DateTime: 'TIMESTAMP',
        Float: 'FLOAT',
        float: 'FLOAT',
    }

    JSON_TYPE = 'JSONB' if dialect == 'postgresql' else 'JSON'

    def _col_type_str(col):
        for typ, sql in TYPE_MAP.items():
            if isinstance(col.type, typ):
                if isinstance(col.type, String) and col.type.length:
                    return f'VARCHAR({col.type.length})'
                return sql
        col_type_name = type(col.type).__name__
        if col_type_name == 'JSON' or col_type_name == 'JSONB':
            return JSON_TYPE
        return 'VARCHAR(255)'

    for table_name, table in db.metadata.tables.items():
        if table_name not in db_tables:
            continue

        try:
            db_columns = {c['name'] for c in inspector.get_columns(table_name)}
        except Exception as exc:
            app_logger.warning(f'Schema sync: could not inspect {table_name}: {exc}')
            continue

        for col in table.columns:
            if col.name in db_columns:
                continue

            type_str = _col_type_str(col)

            try:
                with db.engine.begin() as conn:
                    if dialect == 'postgresql':
                        conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS {col.name} {type_str}'))
                    elif dialect == 'sqlite':
                        sql_type = type_str.replace('TIMESTAMP', 'DATETIME')
                        conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN {col.name} {sql_type}'))
                    else:
                        conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {col.name} {type_str}'))
                app_logger.info(f'Schema sync: added {table_name}.{col.name} ({type_str})')
            except Exception as e:
                app_logger.warning(f'Schema sync: could not add {table_name}.{col.name}: {e}')
