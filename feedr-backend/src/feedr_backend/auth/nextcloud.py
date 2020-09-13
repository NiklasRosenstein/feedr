
from typing import Dict, Optional

import requests
from databind.core import datamodel

from feedr_oauth2 import OAuth2Client, OAuth2Session
from ._base import AuthConfig, AuthPlugin
from ..model.user import User


@datamodel
class NextcloudAuthConfig(AuthConfig):
  base_url: str
  client_id: str
  client_secret: str
  redirect_uri: Optional[str] = None

  def create_authenticator(self, collector_id: str) -> 'NextcloudAuthPlugin':
    base_url = self.base_url.rstrip('/')
    oauth2_client = OAuth2Client(
      f'{base_url}/apps/oauth2/authorize',
      f'{base_url}/apps/oauth2/api/v1/token',
      self.client_id,
      self.client_secret,
      self.redirect_uri,
    )
    return NextcloudAuthPlugin(collector_id, oauth2_client, base_url)


class NextcloudAuthPlugin(AuthPlugin):

  def __init__(self, collector_id: str, oauth2_client: OAuth2Client, base_url: str) -> None:
    self._collector_id = collector_id
    self._oauth2_client = oauth2_client
    self._base_url = base_url

  def create_login_session(self) -> OAuth2Session:
    return self._oauth2_client.login_session()

  def finalize_login(self, access_data: Dict[str, str]) -> User:
    user_id = access_data['user_id']

    user = User.get(
      on=dict(collector_id=self._collector_id, collector_key=str(user_id)),
      or_create=dict(user_name=user_id),
      and_update=dict(avatar_url=None),
    )

    # Fetch the user's avatar.
    auth_header = f'{access_data["token_type"]} {access_data["access_token"]}'
    avatar_url = f'{self._base_url}/avatar/{user_id}/145'
    avatar_response = requests.get(avatar_url, headers={'Authorization': auth_header})
    if avatar_response.status_code // 100 == 2:
      user.save_avatar(avatar_response.content, avatar_response.headers.get('Content-Type'))

    return user
