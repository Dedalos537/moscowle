from contextlib import suppress

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, redirect, url_for
from flask_jwt_extended import create_access_token, create_refresh_token, set_access_cookies, set_refresh_cookies

from app.extensions import db
from app.models.user import User
from app.routes.auth import _record_session

oauth_bp = Blueprint('oauth', __name__, url_prefix='/auth')

_oauth = OAuth()

_google = _oauth.register(
    name='google',
    client_id=None,
    client_secret=None,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

_facebook = _oauth.register(
    name='facebook',
    client_id=None,
    client_secret=None,
    access_token_url='https://graph.facebook.com/v19.0/oauth/access_token',  # noqa: S106
    authorize_url='https://www.facebook.com/v19.0/dialog/oauth',
    client_kwargs={'scope': 'email public_profile'},
)


def _record_oauth_session(user, access_token, refresh_token):
    with suppress(Exception):
        _record_session(user, access_token, refresh_token)


def init_oauth(app):
    _google.client_id = app.config['GOOGLE_CLIENT_ID']
    _google.client_secret = app.config['GOOGLE_CLIENT_SECRET']
    _facebook.client_id = app.config['FACEBOOK_CLIENT_ID']
    _facebook.client_secret = app.config['FACEBOOK_CLIENT_SECRET']
    _oauth.init_app(app)


@oauth_bp.route('/login/google')
def google_login():
    redirect_uri = url_for('oauth.google_callback', _external=True)
    return _google.authorize_redirect(redirect_uri)


@oauth_bp.route('/callback/google')
def google_callback():
    token = _google.authorize_access_token()
    userinfo = _google.parse_id_token(token)
    user = _find_or_create_oauth_user(
        'google',
        userinfo['sub'],
        userinfo.get('email'),
        userinfo.get('name'),
    )
    response = redirect(url_for('main.dashboard'))
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    _record_oauth_session(user, access_token, refresh_token)
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response


@oauth_bp.route('/login/facebook')
def facebook_login():
    redirect_uri = url_for('oauth.facebook_callback', _external=True)
    return _facebook.authorize_redirect(redirect_uri)


@oauth_bp.route('/callback/facebook')
def facebook_callback():
    _facebook.authorize_access_token()
    resp = _facebook.get('https://graph.facebook.com/me?fields=id,name,email')
    profile = resp.json()
    user = _find_or_create_oauth_user(
        'facebook',
        profile['id'],
        profile.get('email'),
        profile.get('name'),
    )
    response = redirect(url_for('main.dashboard'))
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    _record_oauth_session(user, access_token, refresh_token)
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response


def _find_or_create_oauth_user(provider, provider_id, email, name):
    user = User.query.filter_by(oauth_provider=provider, oauth_id=provider_id).first()
    if user:
        return user
    if email:
        user = User.query.filter_by(email=email).first()
        if user:
            user.oauth_provider = provider
            user.oauth_id = provider_id
            db.session.commit()
            return user
    user = User(
        email=email or f'{provider}_{provider_id}@placeholder.moscowle.ai',
        name=name or provider.title(),
        oauth_provider=provider,
        oauth_id=provider_id,
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    return user
