
import flask
from typing import Dict

from ._base import register_component
from .auth import AuthComponent
from .session import SessionManager
from .user import UserComponent
from ..config import Config
from ..model import session, begin_session, end_session


def init_app(app: flask.Flask, config: Config) -> None:
  authenticators = {
    c.collector_id: c.collector.create_authenticator(c.collector_id)
    for c in config.auth.collectors
  }

  @app.before_request
  def _before():
    begin_session()

  @app.teardown_request
  def _teardown(error):
    if error:
      session.rollback()
    else:
      session.commit()
    end_session()

  app.secret_key = config.secret_key

  session_manager = SessionManager(
    login_page_url='/login',
    no_redirect_patterns=['/api/*'],
    token_ttl='P1D',
  )
  register_component(session_manager, app)
  register_component(AuthComponent(authenticators, '/', session_manager), app, '/api/auth')
  register_component(UserComponent(session_manager), app, '/api/user')


def create_app(config: Config) -> flask.Flask:
  app = flask.Flask(__name__)
  init_app(app, config)
  return app
