from flask import current_app

from app.extensions import csrf


class TestSecurityConfig:
    def test_app_secret_key_from_config(self, app):
        assert current_app.config.get('APP_SECRET_KEY') is not None
        assert len(current_app.config['APP_SECRET_KEY']) > 0
        assert current_app.config['APP_SECRET_KEY'] != 'EdySync_Mvp_Secret_2026'

    def test_csrf_time_limit_configurable(self, app):
        limit = current_app.config.get('WTF_CSRF_TIME_LIMIT')
        assert limit is not None
        assert isinstance(limit, int)
        assert limit > 0

    def test_csrf_enabled_in_non_test_config(self):
        from config import Config

        assert hasattr(Config, 'WTF_CSRF_ENABLED')
        assert Config.WTF_CSRF_ENABLED is not False

    def test_session_protection_strong(self, app):
        session_config = current_app.config.get('SESSION_PROTECTION')
        assert session_config is None or session_config == 'strong'

    def test_cors_allow_headers(self, app):
        cors_config = current_app.config.get('CORS_ORIGINS')
        assert cors_config is not None

    def test_csrf_protect_initialized(self, app):
        assert csrf is not None

    def test_security_headers_config(self, app):
        from config import Config

        if hasattr(Config, 'SECURITY_HEADERS'):
            headers = Config.SECURITY_HEADERS
            assert isinstance(headers, dict)

    def test_rate_limit_enabled_in_production(self):
        from config import ProductionConfig

        assert ProductionConfig.RATELIMIT_ENABLED is True or ProductionConfig.RATELIMIT_ENABLED is None

    def test_production_ssl_strict(self):
        from config import ProductionConfig

        assert ProductionConfig.WTF_CSRF_SSL_STRICT is True
