
from typing import Dict, Optional

import requests
from databind.core import datamodel

from feedr_oauth2 import OAuth2Client, OAuth2Session
from ._base import AuthConfig, AuthPlugin
from ..model.user import User


@datamodel
class GithubAuthConfig(AuthConfig):
  authorize_url: str = 'https://github.com/login/oauth/authorize'
  exchange_url: str = 'https://github.com/login/oauth/access_token'
  user_api_url: str = 'https://api.github.com/user'
  client_id: str
  client_secret: str
  redirect_uri: Optional[str] = None

  def create_authenticator(self, collector_id: str) -> 'GithubAuthPlugin':
    oauth2_client = OAuth2Client(
      self.authorize_url,
      self.exchange_url,
      self.client_id,
      self.client_secret,
      self.redirect_uri,
    )
    return GithubAuthPlugin(collector_id, oauth2_client, self.user_api_url)


class GithubAuthPlugin(AuthPlugin):

  def __init__(self, collector_id: str, oauth2_client: OAuth2Client, user_api_url: str) -> None:
    self._collector_id = collector_id
    self._oauth2_client = oauth2_client
    self._user_api_url = user_api_url

  def create_login_session(self) -> OAuth2Session:
    return self._oauth2_client.login_session()

  def finalize_login(self, access_data: Dict[str, str]) -> User:
    user_info = requests.get(
      self._user_api_url,
      headers={'Authorization': 'token ' + access_data['access_token']}).json()
    user = (User
      .get(collector_id=self._collector_id, collector_key=str(user_info['id']))
      .or_create(user_name=user_info['login']))
    user.avatar_url = user_info['avatar_url']
    return user
