"""Enlaces de la app (Angular) que el backend pone en avisos. Las pantallas viven en el frontend; aquí solo se arma
la ruta correcta según el rol de quien recibe el aviso."""

_ROLE_PREFIX = {'admin': '/admin', 'supervisor': '/admin', 'terapista': '/therapist', 'jugador': '/patient'}


def role_path(user_or_id, page):
    """`/admin/messages`, `/therapist/messages`, `/patient/messages`… para el usuario dado (objeto o id)."""
    user = user_or_id
    if isinstance(user_or_id, int):
        from app.extensions import db
        from app.models import User

        user = db.session.get(User, user_or_id)
    prefix = _ROLE_PREFIX.get(getattr(user, 'role', None), '')
    return f'{prefix}/{page.lstrip("/")}' if prefix else '/'
