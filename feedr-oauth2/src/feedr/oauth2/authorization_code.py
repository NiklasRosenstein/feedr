
import enum
import hashlib
import string
import secrets
import typing as t
import uuid
import requests
from urllib.parse import urlencode
from databind.core import datamodel
from .common import AccessTokenResponse, get_token
from .refresh_token import Client as _RefreshTokenClient


@datamodel
class PKCE:
  """
  The Proof Key for Code Exchange (PKCE, pronounced pixie) extension describes a technique for
  public clients to mitigate the threat of having the authorization code intercepted. The
  technique involves the client first creating a secret, and then using that secret again when
  exchanging the authorization code for an access token. This way if the code is intercepted, it
  will not be useful since the token request relies on the initial secret.

  See also https://www.oauth.com/oauth2-servers/pkce/
  """

  class Method(enum.Enum):
    PLAIN = enum.auto()
    SHA256 = enum.auto()

  code_verifier: str
  code_challenge_method: Method

  @staticmethod
  def generate_code_verifier(length: int) -> str:
    if length < 43:
      raise ValueError(f'requested code_verifier length too small: {length}')
    if length > 128:
      raise ValueError(f'requested code_verifier length too large: {length}')
    pool = string.ascii_letters + string.digits + '-._~'
    return ''.join(secrets.choice(pool) for _i in range(length))

  @staticmethod
  def create(length: int = 128, method: Method = Method.SHA256) -> 'PKCE':
    return PKCE(PKCE.generate_code_verifier(length), method)


def get_authorization_request_parameters(
  client_id: str,
  state: str,
  scope: t.Optional[str] = None,
  redirect_uri: t.Optional[str] = None,
  pkce: t.Optional[PKCE] = None,
) -> t.Dict[str, str]:
  """
  Returns the URL query parameters for an OAuth2 user authorization request.
  """

  result = {
    'response_type': 'code',
    'client_id': client_id,
    'state': state,
  }
  if redirect_uri:
    result['redirect_uri'] = redirect_uri
  if scope:
    result['scope'] = scope
  if pkce:
    if pkce.code_challenge_method == PKCE.Method.PLAIN:
      result['code_challenge_method'] = 'plain'
      result['code_challenge'] = pkce.code_verifier
    elif pkce.code_challenge_method == PKCE.Method.SHA256:
      result['code_challenge_method'] = 'S256'
      result['code_challenge'] = hashlib.sha256(pkce.code_verifier.encode('ascii')).hexdigest()
    else:
      raise RuntimeError(f'invalid code_challenge_method: {pkce.code_challenge_method}')
  return result


def get_authorization_code_parameters(
  client_id: str,
  client_secret: str,
  code: str,
  redirect_uri: t.Optional[str] = None,
  pkce: t.Optional[PKCE] = None,
) -> t.Dict[str, str]:
  """
  Returns the URL query parameters for an OAuth2 authorization code request.
  """

  result = {
    'grant_type': 'authorization_code',
    'code': code,
    'client_id': client_id,
    'client_secret': client_secret,
  }
  if redirect_uri:
    result['redirect_uri'] = redirect_uri
  if pkce:
    result['code_verifier'] = pkce.code_verifier
  return result


@datamodel
class Request:
  auth_uri: str
  state: str
  pkce: t.Optional[PKCE]


@datamodel
class Client:
  """
  Represents an OAuth2 client that looks to authenticate with a server using the
  `authorization_code` grant type.
  """

  #: The URL of the server under which a user authorization request can be made. A user will be
  #: redirected to this page including certain parameters to authenticate.
  auth_uri: str

  #: The URL of the authorization server to exchange the authorization code with an access token.
  token_uri: str

  #: The ID of the client application.
  client_id: str

  #: The secret of the client application.
  client_secret: str

  #: The URL to which a user is supposed to be redirected to after the they authenticated with the
  #: authorization server. This URL will receive the authorization code. This can be overwritten
  #: for each individual #authorization_request().
  redirect_uri: t.Optional[str] = None

  #: The scope for the client's permissions with the user's access token. This can be overwritten
  #: for each individual #authorization_request().
  scope: t.Optional[str] = None

  #: Whether to use PKCS.
  use_pkce: bool = False

  #: The session to use when retrieving access token.
  session: t.Optional[requests.Session] = None

  def authorization_request(
    self,
    scope: t.Optional[str] = None,
    redirect_uri: t.Optional[str] = None,
  ) -> Request:
    """
    Creates an authorization request, returning a tuple of the URL that a user must be redirected
    to, the state ID of the request and the #PKCE data for the request. The state ID and PKCE data
    needs to be cached in a way that the #redirect_uri can retrieve the information based on the
    state ID.
    """

    state = str(uuid.uuid4())
    pkce = PKCE.create() if self.use_pkce else None
    parameters = get_authorization_request_parameters(
      self.client_id,
      state,
      self.scope or scope,
      redirect_uri or self.redirect_uri,
      pkce,
    )
    return Request(self.auth_uri + '?' + urlencode(parameters), state, pkce)

  def authorization_code(
    self,
    code: str,
    pkce: t.Optional[PKCE],
    redirect_uri: t.Optional[str] = None,
    session: t.Optional[requests.Session] = None,
  ) -> AccessTokenResponse:
    """
    Performa a POST request to the #token_uri to exchange the authorization *code* for an
    access token.
    """

    if self.use_pkce and not pkce:
      raise RuntimeError('use_pkce is enabled but no PKCE was passed')
    elif not self.use_pkce and pkce:
      raise RuntimeError('use_pkce is disabled but a PKCE was passed')

    parameters = get_authorization_code_parameters(
      self.client_id,
      self.client_secret,
      code,
      redirect_uri,
      pkce,
    )

    return get_token(self.token_uri, parameters, session or self.session)

  def refresh_token(
    self,
    refresh_token: str,
    scope: t.Optional[str] = None,
    session: t.Optional[requests.Session] = None,
  ) -> AccessTokenResponse:
    client = _RefreshTokenClient(
      self.token_uri,
      refresh_token,
      scope or self.scope,
      self.client_id,
      self.client_secret,
      session or self.session,
    )
    return client.get_token()
