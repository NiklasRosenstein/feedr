
from pathlib import Path
from typing import Dict, Union

from databind.core import datamodel, uniontype
from databind.yaml import from_str

from .auth import AuthHandlerConfig


@datamodel
class DatabaseConfig:
  url: str


@datamodel
class Auth:
  handlers: Dict[str, AuthHandlerConfig]


@datamodel
class Config:
  auth: Auth
  database: DatabaseConfig
  secret_key: str
  media_directory: str

  @classmethod
  def load(cls, file_: Union[str, Path]) -> 'Config':
    return from_str(cls, Path(file_).read_text())
