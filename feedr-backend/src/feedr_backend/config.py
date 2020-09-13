
from pathlib import Path
from typing import List, Union

from databind.core import datamodel, uniontype
from databind.yaml import from_str

from .auth import AuthConfig, AuthPlugin
from .auth.github import GithubAuthConfig


@datamodel
class DatabaseConfig:
  url: str


@uniontype
class Authenticator(AuthConfig):
  github: GithubAuthConfig


@datamodel
class Collector:
  collector_id: str
  collector: Authenticator


@datamodel
class Auth:
  collectors: List[Collector]


@datamodel
class Config:
  auth: Auth
  database: DatabaseConfig

  @classmethod
  def load(cls, file_: Union[str, Path]) -> 'Config':
    return from_str(cls, Path(file_).read_text())
