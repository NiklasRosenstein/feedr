
import abc
from typing import Any, Dict, Optional

import flask
from databind.core import datamodel, interface
from databind.json import from_json, to_json
from nr.parsing.date import Duration

from feedr_oauth2 import OAuth2Client, OAuth2Session, OAuth2SessionData
from ..model.user import User
from ..app._base import Component, route, url_for

__all__ = [
  'LoginStateRecorder',
  'AuthContext',
  'AuthHandlerConfig',
  'AuthHandler',
  'OAuth2Handler',
]


class LoginStateRecorder(metaclass=abc.ABCMeta):
  """
  Abstract base class of which an instance is handed to an #AuthHandler to record login
  state, allowing login processes to run run over multiple requests.
  """

  class ExpiredState(Exception):
    pass

  class UnknownState(Exception):
    pass

  @abc.abstractmethod
  def create_state(self, state_id: str, expires_in: Duration, data: Dict[str, Any]) -> None:
    """
    Record a state with the specified *state_id*, which has to be unique (e.g. a UUID). The
    state is set to expire by *expires_in* from the current time. The *data* must be JSON
    serializable and is stored alongside the state and can be retrieved with #get_state().
    """

  @abc.abstractmethod
  def get_state(self, state_id: str, consume: bool = False) -> Dict[str, Any]:
    """
    Read a state that was previously created with #create_state(). An #ExpiredState error may be
    raised if it is retrieved shortly after the state expired, but there is no garuantee on the
    lifetime of any state information (i.e. if it existed in the first place) past expiration.

    If *consume* is set to #True, the state will be removed from the state recorder (this is
    the same as calling #consume_state() right afterwards).
    """

  @abc.abstractmethod
  def consume_state(self, state_id: str) -> None:
    """
    Consume a state, removing it's record from the recorder.
    """

  @abc.abstractmethod
  def login(self, user: User) -> None:
    """
    Updates session cookies to reflect the user's login state.
    """


@datamodel
class AuthContext:
  id: str
  state_recorder: LoginStateRecorder
  redirect_uri: str


@interface
class AuthHandlerConfig(metaclass=abc.ABCMeta):
  """
  Abstract base class for describing the configuration of an #AuthHandler.
  """

  @abc.abstractmethod
  def get_auth_handler(self, context: AuthContext) -> 'AuthHandler':
    pass


class AuthHandler(Component, metaclass=abc.ABCMeta):
  """
  Abstract base class for authenticators. Authenticators are also components that are
  mounted into the application.
  """

  def __init__(self, context: AuthContext) -> None:
    self.context = context

  @abc.abstractmethod
  def get_description(self) -> Dict[str, Any]:
    """
    Returns a description for the authenticator for consumers. The returned value must be
    JSON serializable.
    """


class OAuth2Handler(AuthHandler):
  """
  Implements the base for an OAuth2 authenticator providing a `login` and `authorize` flow.

  The default session ttl is 5 minutes.
  """

  def __init__(
    self,
    context: AuthContext,
    oauth2: OAuth2Client,
    session_ttl: Optional[Duration] = None,
  ) -> None:
    super().__init__(context)
    self.oauth2 = oauth2
    self.session_ttl = session_ttl or Duration(minutes=5)

  def get_description(self) -> Dict[str, Any]:
    return {'type': 'oauth2', 'url': url_for(self.login)}

  @route('/login')
  def login(self) -> flask.Response:
    redirect_uri = flask.request.args.get('redirect_uri')
    session = self.oauth2.login_session()
    data = {'session': to_json(session.data), 'redirect_uri': redirect_uri}
    self.context.state_recorder.create_state(session.data.state, self.session_ttl, data)
    return flask.redirect(session.login_url)

  @route('/authorize')
  def authorize(self) -> flask.Response:
    code = flask.request.args['code']
    state = flask.request.args['state']
    data = self.context.state_recorder.get_state(state, consume=True)
    session = OAuth2Session(from_json(OAuth2SessionData, data['session']), self.oauth2)
    access_data = session.get_token(code)
    redirect_uri = data['redirect_uri'] or self.context.redirect_uri
    user = self.finalize_login(access_data)
    self.context.state_recorder.login(user)
    return flask.redirect(redirect_uri)

  @abc.abstractmethod
  def finalize_login(self, access_data: Dict[str, str]) -> User:
    pass
