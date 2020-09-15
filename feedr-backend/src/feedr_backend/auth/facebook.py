
from typing import Dict, Optional

import requests
from databind.core import datamodel, implementation

from feedr_oauth2 import OAuth2Client
from ._base import AuthContext, AuthHandlerConfig, OAuth2Handler
from ..model import session
from ..model.task import BaseTask, queue_task
from ..model.user import User
from ..model.task import queue_task

FACEBOOK_BASE_URL = 'https://www.facebook.com'
FACEBOOK_GRAPH_URL = 'https://graph.facebook.com'


@datamodel
@implementation('facebook')
class FacebookAuthHandlerConfig(AuthHandlerConfig):
  client_id: str
  client_secret: str
  redirect_uri: str

  def get_auth_handler(self, context: AuthContext) -> 'FacebookOAuth2Handler':
    oauth2 = OAuth2Client(
      f'{FACEBOOK_BASE_URL}/v8.0/dialog/oauth',
      f'{FACEBOOK_GRAPH_URL}/v8.0/oauth/access_token',
      self.client_id,
      self.client_secret,
      self.redirect_uri,
    )
    return FacebookOAuth2Handler(context, oauth2)


class FacebookOAuth2Handler(OAuth2Handler):

  def finalize_login(self, access_data: Dict[str, str]) -> User:
    data = requests.get(
      f'{FACEBOOK_GRAPH_URL}/me',
      params={'access_token': access_data['access_token'], 'fields': 'id,name'}).json()

    user = (User
      .get(collector_id=self.context.id, collector_key=data['id'])
      .or_create(user_name=data['name']))

    queue_task(
      f'Download Facebook Profile Picture for user {data["id"]}',
      RefreshAvatar(user.id, data['id']))

    return user


@datamodel
class RefreshAvatar(BaseTask):
  user_id: int
  facebook_user_id: str

  def execute(self):
    user = User.get(id=self.user_id).instance
    url = f'{FACEBOOK_GRAPH_URL}/v8.0/{self.facebook_user_id}/picture'
    user.refresh_avatar(url, params={'height': 150})
