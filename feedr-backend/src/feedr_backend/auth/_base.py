
import abc
from typing import Dict

from feedr_oauth2 import OAuth2Session
from ..model.user import User


class AuthConfig(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def create_authenticator(self, collector_id: str) -> 'AuthPlugin':
    pass


class AuthPlugin(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def create_login_session(self) -> OAuth2Session:
    pass

  @abc.abstractmethod
  def finalize_login(self, access_data: Dict[str, str]) -> User:
    pass
