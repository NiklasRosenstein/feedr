
import abc
import enum
import hashlib
import secrets
import string
import typing as t
import uuid
from urllib.parse import parse_qsl, urlencode

import requests
from databind.core import datamodel, field

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.1.0'



if t.TYPE_CHECKING:
  class OAuth2StateFactory(t.Protocol):
    def __call__(self) -> str:
      pass


class OAuth2Exception(Exception):
  pass


@datamodel
class OAuth2Client:
  authorize_url: str
  exchange_url: str
  client_id: str
  client_secret: str
  redirect_uri: t.Optional[str] = None
  state_factory: 'OAuth2StateFactory' = field(default=lambda: str(uuid.uuid4()))

  def login_session(self,
    state: t.Optional[str] = None,
    login: t.Optional[str] = None,
    response_type: str = 'code',
    grant_type: str = 'authorization_code',
  ) -> 'OAuth2Session':
    data = OAuth2SessionData(state or self.state_factory(), login, response_type, grant_type)
    return OAuth2Session(data, self)


@datamodel
class OAuth2SessionData:
  state: str
  login: t.Optional[str]
  response_type: str
  grant_type: str

  @classmethod
  def from_json(cls, data: t.Dict[str, t.Any]) -> 'OAuth2SessionData':
    from databind.json import from_json
    return from_json(cls, data)

  def to_json(self) -> t.Dict[str, t.Any]:
    from databind.json import to_json
    return t.cast(t.Dict[str, t.Any], to_json(self))


@datamodel
class OAuth2Session:
  data: OAuth2SessionData
  client: OAuth2Client

  @property
  def login_url(self) -> str:
    params = {
      'client_id': self.client.client_id,
      'state': self.data.state,
      'response_type': self.data.response_type,
    }
    if self.data.login:
      params['login'] = self.data.login
    if self.client.redirect_uri:
      params['redirect_uri'] = self.client.redirect_uri
    return self.client.authorize_url + '?' + urlencode(params)

  def token_url(self, code: str) -> str:
    params = {
      'client_id': self.client.client_id,
      'client_secret': self.client.client_secret,
      'code': code,
      'state': self.data.state,
      'grant_type': self.data.grant_type,
    }
    if self.client.redirect_uri:
      params['redirect_uri'] = self.client.redirect_uri
    return self.client.exchange_url + '?' + urlencode(params)

  def get_token(self, code: str) -> t.Dict[str, str]:
    assert self.data.grant_type == 'authorization_code'
    response = requests.post(self.token_url(code))
    response.raise_for_status()
    content_type = response.headers.get('Content-Type', '').partition(';')[0]
    if content_type == 'application/json':
      return response.json()
    elif content_type == 'application/x-www-form-urlencoded':
      return dict(parse_qsl(response.text))
    else:
      raise RuntimeError(f'unknown Content-Type: {content_type!r}')
