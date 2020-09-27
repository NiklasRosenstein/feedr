
"""
The Refresh Token grant type is used by clients to exchange a refresh token for an access token
when the access token has expired.

This allows clients to continue to have a valid access token without further interaction with
the user.

See also https://oauth.net/2/grant-types/refresh-token/
"""

import typing as t
import requests
from databind.core import datamodel
from .common import AccessTokenResponse, get_token


def get_refresh_token_parameters(
  refresh_token: str,
  scope: t.Optional[str],
  client_id: t.Optional[str] = None,
  client_secret: t.Optional[str] = None,
) -> t.Dict[str, str]:

  if (client_id or client_secret) and not (client_id and client_secret):
    raise ValueError('client_id and client_secret must both or neither be present')

  result = {
    'grant_type': 'refresh_token',
    'refresh_token': refresh_token,
  }
  if scope:
    result['scope'] = scope
  if client_id and client_secret:
    result.update({
      'client_id': client_id,
      'client_secret': client_secret,
    })
  return result


@datamodel
class Client:

  token_uri: str

  #: The refresh token previously issue to the client.
  refresh_token: str

  #: The requested scope must not include additional scopes that were not issued in the original
  #: access token. Typically this will not be included in the request, and if omitted, the service
  #: should issue an access token with the same scope as was previously issued.
  scope: t.Optional[str] = None

  #: The client ID and secret are optional if the client has not been granted a secret.
  client_id: t.Optional[str] = None
  client_secret: t.Optional[str] = None

  session: t.Optional[requests.Session] = None

  def get_token(
    self,
    scope: t.Optional[str] = None,
    session: t.Optional[requests.Session] = None,
  ) -> AccessTokenResponse:

    parameters = get_refresh_token_parameters(
      self.refresh_token,
      scope or self.scope,
      self.client_id,
      self.client_secret,
    )

    return get_token(self.token_uri, parameters, session or self.session)
