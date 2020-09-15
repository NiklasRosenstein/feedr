
from pathlib import Path
from typing import Dict, Union

from databind.core import datamodel, field, uniontype
from databind.yaml import from_str
from nr.parsing.date import Duration

from .auth import AuthHandlerConfig


@datamodel
class DatabaseConfig:
  url: str


@datamodel
class Auth:
  handlers: Dict[str, AuthHandlerConfig]


@datamodel
class RssConfig:
  update_interval: Duration = Duration.parse('PT10M')


@datamodel
class Config:
  debug: bool = False
  auth: Auth
  database: DatabaseConfig
  secret_key: str
  media_directory: str
  rss: RssConfig = field(default_factory=RssConfig)

  @classmethod
  def load(cls, file_: Union[str, Path]) -> 'Config':
    return from_str(cls, Path(file_).read_text())
