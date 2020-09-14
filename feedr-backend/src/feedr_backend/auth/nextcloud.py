
from typing import Dict, Optional

import requests
from databind.core import datamodel

from feedr_oauth2 import OAuth2Client, OAuth2Session
from ._base import AuthConfig, AuthPlugin
from ..model import session
from ..model.task import BaseTask, queue_task
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
    user = (User
      .get(collector_id=self._collector_id, collector_key=user_id)
      .or_create(user_name=user_id))
    session.commit()  # TODO: Is this a good idea? Maybe wrap user in it's own context.

    auth_header = f'{access_data["token_type"]} {access_data["access_token"]}'
    avatar_url = f'{self._base_url}/avatar/{user_id}/145'
    queue_task(
      f'Refresh Avatar for User {user.id}',
      RefreshAvatar(user.id, auth_header, avatar_url))

    return user


@datamodel
class RefreshAvatar(BaseTask):
  user_id: int
  auth_header: str
  avatar_url: str

  def execute(self):
    user = User.get(id=self.user_id).instance
    # TODO: Download only if user avatar is already the same.
    response = requests.get(self.avatar_url, headers={'Authorization': self.auth_header})
    if response.status_code // 100 == 2:
      user.save_avatar(response.content, response.headers['Content-Type'])
