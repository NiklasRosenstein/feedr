
"""
The Device Code grant type is used by browserless or input-constrained devices in the device
flow to exchange a previously obtained device code for an access token.

See also https://oauth.net/2/grant-types/device-code/
"""

import time
import typing as t
import requests
from urllib.parse import urlencode
from databind.core import datamodel
from databind.json import from_json
from .common import AccessTokenResponse, get_default_session, get_token_polling, raise_for_response


def get_device_code_parameters(client_id: str, client_secret: str, device_code: str) -> t.Dict[str, str]:
  return {
    'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
    'client_id': client_id,
    'client_secret': client_secret,
    'device_code': device_code,
  }


@datamodel
class DeviceCodeResponse:
  device_code: str
  user_code: str
  verification_url: str
  interval: int
  expires_in: t.Optional[int] = None


@datamodel
class Client:

  #: The URL where a device code can be requested.
  device_code_uri: str

  #: The URL that can be polled to convert the device code.
  token_uri: str

  #: The ID of the client.
  client_id: str

  #: The client secret.
  client_secret: str

  #: The scope of the device code.
  scope: t.Optional[str] = None

  session: t.Optional[requests.Session] = None

  def get_device_code(
    self,
    scope: t.Optional[str] = None,
    session: t.Optional[requests.Session] = None,
  ) -> DeviceCodeResponse:

    parameters = {'client_id': self.client_id}
    if scope or self.scope:
      parameters['scope'] = t.cast(str, scope or self.scope)

    session = session or self.session or get_default_session()
    response = session.post(self.device_code_uri, data=parameters)
    raise_for_response(response)
    return from_json(DeviceCodeResponse, response.json())

  def poll(
    self,
    info: DeviceCodeResponse,
    timeout: t.Optional[int] = None,
    session: t.Optional[requests.Session] = None,
  ) -> AccessTokenResponse:

    parameters = get_device_code_parameters(
      self.client_id,
      self.client_secret,
      info.device_code,
    )

    if timeout is None:
      if info.expires_in is not None:
        timeout = info.expires_in
    else:
      if info.expires_in is not None:
        timeout = min(timeout, info.expires_in)

    return get_token_polling(
      self.token_uri,
      parameters,
      info.interval,
      timeout,
      session or self.session,
    )
