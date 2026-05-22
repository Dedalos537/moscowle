
swagger_config = {
    'headers': [],
    'specs': [
        {
            'endpoint': 'apispec',
            'route': '/api/swagger.json',
            'rule_filter': lambda rule: rule.rule.startswith('/api/'),
            'model_filter': lambda tag: True,
        }
    ],
    'static_url_path': '/flasgger_static',
    'swagger_ui': True,
    'specs_route': '/api/docs/',
}

swagger_template = {
    'swagger': '2.0',
    'info': {
        'title': 'Moscowle IA API',
        'description': 'API for Moscowle IA - Therapy management platform',
        'version': '1.0.0',
    },
    'basePath': '/',
    'schemes': ['https', 'http'],
    'securityDefinitions': {
        'SessionAuth': {
            'type': 'apiKey',
            'name': 'Cookie',
            'in': 'header',
            'description': 'Flask session cookie (moscowle_session) for authenticated requests'
        }
    },
}
