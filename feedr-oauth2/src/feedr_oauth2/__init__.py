
import requests
import uuid
from databind.core import datamodel, field
from typing import Callable, Dict, Optional
from urllib.parse import parse_qsl, urlencode

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.0.0'


class OAuth2Exception(Exception):
  pass


class TamperedFlowException(OAuth2Exception):
  """
  This exception is raised if the OAuth2 flow was tampered with (e.g. if the `code` or `state`
  of the redirect does not match what was originally sent).
  """


@datamodel
class OAuth2Client:
  authorize_url: str
  exchange_url: str
  client_id: str
  client_secret: str
  redirect_uri: Optional[str] = None
  state_factory: Callable[[], str] = field(default=lambda: str(uuid.uuid4()))

  def login_session(self,
    state: Optional[str] = None,
    login: Optional[str] = None,
  ) -> 'OAuth2Session':
    return OAuth2Session(self, state or self.state_factory(), login)


@datamodel
class OAuth2Session:
  client: OAuth2Client
  state: str
  login: Optional[str]

  @property
  def login_url(self) -> str:
    params = {
      'client_id': self.client.client_id,
      'state': self.state,
    }
    if self.login:
      params['login'] = self.login
    if self.client.redirect_uri:
      params['redirect_uri'] = self.client.redirect_uri,
    return self.client.authorize_url + '?' + urlencode(params)

  def validate(self, state: Optional[str]) -> None:
    assert self.state is not None
    if self.state != state:
      raise TamperedFlowException(f'OAuth2 state mismatch ({self.state!r} != {state!r})')

  def exchange_url(self, code: str) -> str:
    params = {
      'client_id': self.client.client_id,
      'client_secret': self.client.client_secret,
      'code': code,
      'state': self.state,
    }
    if self.client.redirect_uri:
      params['redirect_uri'] = self.client.redirect_uri
    return self.client.exchange_url + '?' + urlencode(params)

  def exchange(self, code: str) -> Dict[str, str]:
    response = requests.post(self.exchange_url(code))
    response.raise_for_status()
    return dict(parse_qsl(response.text))
