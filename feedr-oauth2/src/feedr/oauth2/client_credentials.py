
"""
The Client Credentials grant is used when applications request an access token to access their
own resources, not on behalf of a user.

See also https://www.oauth.com/oauth2-servers/access-tokens/client-credentials/
"""


import typing as t
import requests
from urllib.parse import urlencode
from databind.core import datamodel
from .commons import AccessTokenResponse, get_token


def get_client_credentials_parameters(
  client_id: str,
  client_secret: str,
  scope: t.Optional[str] = None,
) -> t.Dict[str, str]:
  result = {
    'grant_type': 'client_credentials',
    'client_id': client_id,
    'client_secret': client_secret,
  }
  if scope:
    result['scope'] = scope
  return result


@datamodel
class Client:

  #: The URL on which a token can be exchanged.
  token_uri: str

  #: The client needs to authenticate themselves for this request. Typically the service will
  #: allow additional request parameters client_id and client_secret.
  client_id: str
  client_secret: str

  #: Your service can support different scopes for the client credentials grant. In practice, not
  #: many services actually support this.
  scope: t.Optional[str] = None

  session: t.Optional[requests.Session] = None

  def get_token(
    self,
    scope: t.Optional[str] = None,
    session: t.Optional[requests.Session] = None,
  ) -> AccessTokenResponse:

    parameters = get_client_credentials_parameters(
      self.client_id,
      self.client_secret,
      scope or self.scope,
    )

    return get_token(self.token_uri, parameters, session or self.session)
