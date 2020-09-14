
from typing import Dict, Optional

import requests
from databind.core import datamodel, implementation

from feedr_oauth2 import OAuth2Client, OAuth2Session
from ._base import AuthContext, AuthHandlerConfig, OAuth2Handler
from ..model.user import User


@datamodel
@implementation('github')
class GithubAuthHandlerConfig(AuthHandlerConfig):
  authorize_url: str = 'https://github.com/login/oauth/authorize'
  exchange_url: str = 'https://github.com/login/oauth/access_token'
  user_api_url: str = 'https://api.github.com/user'
  client_id: str
  client_secret: str
  redirect_uri: Optional[str] = None

  def get_auth_handler(self, context: AuthContext) -> 'GithubOAuth2Handler':
    oauth2 = OAuth2Client(
      self.authorize_url,
      self.exchange_url,
      self.client_id,
      self.client_secret,
      self.redirect_uri,
    )
    return GithubOAuth2Handler(context, oauth2, self)


class GithubOAuth2Handler(OAuth2Handler):

  def __init__(self, context: AuthContext, oauth2: OAuth2Client, config: GithubAuthHandlerConfig) -> None:
    super().__init__(context, oauth2)
    self.config = config

  def finalize_login(self, access_data: Dict[str, str]) -> User:
    auth_header = f'{access_data["token_type"]} {access_data["access_token"]}'
    user_info = requests.get(
      self.config.user_api_url,
      headers={'Authorization': auth_header}).json()

    user = (User
      .get(collector_id=self.context.id, collector_key=str(user_info['id']))
      .or_create(user_name=user_info['login']))
    user.avatar_url = user_info['avatar_url']

    return user
