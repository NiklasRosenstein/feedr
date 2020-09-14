
import datetime
import logging
import threading
from fnmatch import fnmatch
from typing import List, Optional, Union, cast

import flask
from nr.parsing.date import Duration
from sqlalchemy.orm.exc import NoResultFound

from ._base import Component
from ..auth import LoginStateRecorder
from ..model import session
from ..model.user import User, Token, LoginState

logger = logging.getLogger(__name__)


class SessionManager(Component, LoginStateRecorder):

  def __init__(self,
    login_page_url: Optional[str],
    no_redirect_patterns: List[str],
    token_ttl: Union[str, Duration],
    cookie_name: str = 'FEEDR_TOKEN',
  ) -> None:
    if isinstance(token_ttl, str):
      token_ttl = Duration.parse(token_ttl)
    self._login_page_url = login_page_url
    self._no_redirect_patterns = no_redirect_patterns
    self._token_ttl = token_ttl
    self._cookie_name = cookie_name
    self._local = threading.local()

  @property
  def current_token(self) -> Optional[Token]:
    return cast(Optional[Token], self._local.token)

  @property
  def current_user(self) -> Optional[User]:
    if self._local.token:
      return cast(User, self._local.token.user)
    return None

  def logout(self) -> None:
    token = self.current_token
    if token:
      logger.info('Logging out user "%s" with token ID %s', token.user.id, token.id)
      token.revoke()
      session.pop(self._cookie_name, None)

  # Component

  def before_request(self):
    token_value = flask.session.get(self._cookie_name)
    token = None
    if token_value is not None:
      token = Token.get(value=token_value).or_none()
      if token and not token.is_valid:
        token = None
    self._local.token = token
    if (not self._local.token and
        self._login_page_url and
        flask.request.path != self._login_page_url and
        not any(fnmatch(flask.request.path, p) for p in self._no_redirect_patterns)):
      logger.info('Redirecting to login page "%s"', self._login_page_url)
      return flask.redirect(self._login_page_url)

  # LoginStateRecorder

  def create_state(self, state_id, expires_in, data):
    session.add(LoginState(
      id=state_id,
      expires_at=datetime.datetime.utcnow() + expires_in.as_timedelta(),
      data=data))

  def get_state(self, state_id, consume=False):
    try:
      state = LoginState.get(id=state_id).instance
    except NoResultFound:
      raise LoginStateRecorder.UnknownState
    if state.is_expired:
      raise LoginStateRecorder.ExpiredState
    if consume:
      session.delete(state)
    return state.data

  def consume_state(self, state_id):
    self.get_state(state_id, True)

  def login(self, user: User) -> None:
    expiration_date = datetime.datetime.utcnow() + self._token_ttl.as_timedelta()
    self._local.token = user.create_token(expiration_date)
    logger.info('Logging in user "%s" with token ID %s', user.id, self._local.token.id)
    flask.session[self._cookie_name] = self._local.token.value
