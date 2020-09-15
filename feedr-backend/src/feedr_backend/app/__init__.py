
import flask
from typing import Dict

from ._base import register_component
from .auth import AuthComponent
from .session import SessionManager
from .user import UserComponent
from ..config import Config
from ..model import session


def init_app(app: flask.Flask, config: Config) -> None:

  @app.teardown_request
  def _teardown(error):
    if error:
      session.rollback()
    else:
      session.commit()
    session.remove()

  app.secret_key = config.secret_key

  session_manager = SessionManager(
    login_page_url='/login',
    no_redirect_patterns=['/api/*'],
    token_ttl='P1D',
  )

  auth = AuthComponent(config.auth.handlers, session_manager, '/')

  register_component(session_manager, app)
  register_component(auth, app, '/api/auth')
  register_component(UserComponent(session_manager), app, '/api/user')


def create_app(config: Config) -> flask.Flask:
  app = flask.Flask(__name__)
  init_app(app, config)
  return app
