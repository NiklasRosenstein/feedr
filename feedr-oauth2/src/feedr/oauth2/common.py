
import abc
import typing as t
import sys
import time
import requests
from urllib.parse import parse_qsl, urlencode
from databind.core import datamodel
from databind.json import from_json
from . import __version__


class OAuth2Error(Exception):
  pass


class SlowDown(OAuth2Error):
  pass


class AuthorizationPending(OAuth2Error):
  pass


class RateLimitedExceeded(OAuth2Error):
  pass


class InvalidRequest(OAuth2Error):
  pass


class Timeout(OAuth2Error):
  pass


def raise_for_error_code(error_code: str) -> None:
  if error_code == 'authorization_pending':
    raise AuthorizationPending()
  elif error_code == 'slow_down':
    raise SlowDown()
  elif error_code == 'rate_limit_exceeded':
    raise RateLimitedExceeded()
  elif error_code == 'invalid_request':
    raise InvalidRequest()
  else:
    raise OAuth2Error(f'Unknown error: {error_code!r}')


def raise_for_response(response: requests.Response) -> None:
  if response.status_code // 100 not in (4, 5):
    return
  if 'application/json' not in response.headers.get('Content-Type', ''):
    response.raise_for_status()
  error_code = response.json().get('error')
  if not error_code:
    raise OAuth2Error('An unknown error occurred')
  raise_for_error_code(error_code)


@datamodel
class AccessTokenResponse:
  access_token: str
  token_type: str
  expires_in: t.Optional[int] = None
  refresh_token: t.Optional[str] = None
  scope: t.Optional[str] = None

  @staticmethod
  def from_response(response: requests.Response) -> 'AccessTokenResponse':
    raise_for_response(response)
    content_type = response.headers.get('Content-Type', '').partition(';')[0]
    if content_type == 'application/json':
      raw = response.json()
    elif content_type == 'application/x-www-form-urlencoded':
      raw = dict(parse_qsl(response.text))
    else:
      raise RuntimeError(f'unsupported Content-Type: {content_type!r}')
    return from_json(AccessTokenResponse, raw)


def get_user_agent() -> str:
  return f'Python-{sys.version.split(" ")[0]}/feedr.oauth2-{__version__}'


def get_default_session() -> requests.Session:
  session = requests.Session()
  session.headers['User-Agent'] = get_user_agent()
  return session


def get_token(
  token_url: str,
  params: t.Dict[str, str],
  session: t.Optional[requests.Session] = None,
) -> AccessTokenResponse:

  url = token_url + '?' + urlencode(params)
  session = session or get_default_session()
  response = session.post(url)
  return AccessTokenResponse.from_response(response)


def get_token_polling(
  token_url: str,
  params: t.Dict[str, str],
  interval: int,
  timeout: t.Optional[int],
  session: t.Optional[requests.Session] = None,
) -> AccessTokenResponse:

  session = session or get_default_session()
  start_time = time.perf_counter()
  end_time = start_time + timeout if timeout else None

  while end_time is None or time.perf_counter() < end_time:
    try:
      return get_token(token_url, params, session)
    except SlowDown:
      interval += 1  # TODO: Configurable back off strategy
    except AuthorizationPending:
      pass
    time.sleep(interval)

  raise Timeout(token_url, timeout)
