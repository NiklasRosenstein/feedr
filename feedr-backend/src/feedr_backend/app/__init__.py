
import flask
from typing import Dict

from ._base import register_component
from .auth import AuthComponent
from ..config import Config
from ..model import session, begin_session, end_session

app = flask.Flask(__name__)


def init_app(config: Config) -> None:
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

  register_component(AuthComponent(authenticators), app, '/api/auth')
