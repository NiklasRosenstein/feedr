
import abc
import typing as t
import flask

_CONFIG_KEY = 'FEEDR_CORE_MIME_SERDE'


class Serde(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def read_body(self, request: flask.Request, annotated_type: t.Any) -> t.Any:
    ...

  @abc.abstractmethod
  def read_header(self, request: flask.Request, annotated_type: t.Any) -> t.Any:
    ...

  @abc.abstractmethod
  def read_query(self, request: flask.Request, annotated_type: t.Any) -> t.Any:
    ...

  @abc.abstractmethod
  def write(self, annotated_type: t.Any, result: t.Any, status_code: int, headers: t.Any) -> flask.Response:  # TODO: stricter types
    ...

  @abc.abstractmethod
  def handle_error(self, error: BaseException) -> flask.Response:
    ...


def register_serde(app: flask.Flask, content_type: str, serde: Serde) -> None:
  if _CONFIG_KEY not in app.config:
    app.config[_CONFIG_KEY] = {}
  app.config[_CONFIG_KEY][content_type] = serde


def get_serde(app: flask.Flask, content_type: str) -> Serde:
  return app.config[_CONFIG_KEY][content_type]
