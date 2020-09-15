
from typing import Dict, Optional

import requests
from databind.core import datamodel, implementation

from feedr_oauth2 import OAuth2Client
from ._base import AuthContext, AuthHandlerConfig, OAuth2Handler
from ..model import session
from ..model.task import BaseTask, queue_task
from ..model.user import User


@datamodel
@implementation('nextcloud')
class NextcloudAuthHandlerConfig(AuthHandlerConfig):
  base_url: str
  client_id: str
  client_secret: str
  redirect_uri: Optional[str] = None

  def get_auth_handler(self, context: AuthContext) -> 'NextcloudOAuth2Handler':
    base_url = self.base_url.rstrip('/')
    oauth2 = OAuth2Client(
      f'{base_url}/apps/oauth2/authorize',
      f'{base_url}/apps/oauth2/api/v1/token',
      self.client_id,
      self.client_secret,
      self.redirect_uri,
    )
    return NextcloudOAuth2Handler(context, oauth2, base_url)


class NextcloudOAuth2Handler(OAuth2Handler):

  def __init__(self, context: AuthContext, oauth2: OAuth2Client, base_url: str) -> None:
    super().__init__(context, oauth2)
    self.base_url = base_url

  def finalize_login(self, access_data: Dict[str, str]) -> User:
    user_id = access_data['user_id']
    user = (User
      .get(collector_id=self.context.id, collector_key=user_id)
      .or_create(user_name=user_id))
    session.commit()

    auth_header = f'{access_data["token_type"]} {access_data["access_token"]}'
    avatar_url = f'{self.base_url}/avatar/{user_id}/145'
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
    user.refresh_avatar(self.avatar_url, headers={'Authorization': self.auth_header})
