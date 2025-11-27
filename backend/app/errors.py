from flask import jsonify


class ServiceError(Exception):
    """Generic service-level exception for business rule violations."""


class NotFoundError(ServiceError):
    pass


class ConflictError(ServiceError):
    pass


def register_error_handlers(app):
    @app.errorhandler(ServiceError)
    def handle_service_error(err):
        code = 404 if isinstance(err, NotFoundError) else 400
        return jsonify({"error": type(err).__name__, "message": str(err)}), code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        # Do not leak internals in production; log stack elsewhere
        return jsonify({"error": "InternalServerError", "message": "An unexpected error occurred."}), 500
