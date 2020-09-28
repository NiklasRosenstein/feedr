

"""
import enum
import json
import typing as t
from dataclasses import dataclass

import databind.core
import databind.json
import flask
import werkzeug.exceptions
from feedr_core.attach import attach, register_attachment_type, retrieve
from feedr_core.web.route import Route
from feedr_core.web.view import View, Response


@dataclass
class ErrorDescription:
  message: str
  parameters: t.Dict[str, t.Any]



def abort(self, code: int, message: str, parameters: t.Dict[str, t.Any]) -> None:
  flask.abort(code, ErrorDescription(message, parameters))
"""

import json
import typing as t
import flask
from databind.core import Registry
from databind.json import from_json, to_json
from .serde import Serde


def json_response(body: t.Dict[str, t.Any], code: int, headers: t.Any) -> flask.Response:
  # TODO: Serialize as a stream to avoid filling up memory for large responses?
  if isinstance(headers, t.Sequence):
    headers = dict(headers)
  headers['Content-Type'] = 'application/json'
  return flask.make_response(json.dumps(body), code, headers)


class JsonSerde(Serde):
  """
  Implements a serializer/deserializer for routes with content type `application/json`.
  """

  def __init__(self, json_registry: t.Optional[Registry] = None) -> None:
    self.json_registry = json_registry

  def read_body(self, request, annotated_type):
    return from_json(annotated_type, request.json, registry=self.json_registry)

  def read_header(self, request, annotated_type, value):
    return from_json(annotated_type, value, registry=self.json_registry)

  def read_query(self, request, annotated_type, value):
    return from_json(annotated_type, value, registry=self.json_registry)

  def write(self, annotated_type, result, code, headers):
    return json_response(to_json(result, annotated_type), code, headers)

  def handle_error(self, error):
    if isinstance(error, werkzeug.erroreptions.HTTPException):
      if isinstance(error.description, str):
        description = ErrorDescription(error.description, {})
      elif isinstance(error.description, t.Mapping):
        description = ErrorDescription(type(error).description, error.description)
      elif isinstance(error.description, ErrorDescription):
        description = error.description
      else:
        description = ErrorDescription(str(error.description), {})
      payload = {
        'errorName': error.name,
        'message': description.message,
        'parameters': description.parameters,
      }
      status_code = t.cast(int, error.code)
    else:
      payload = {
        'errorName': 'Internal Server Error',
        'message': 'An unexpected internal error occurred.',
        'parameters': {},
      }
      status_code = 500
    return json_response(payload, status_code, [])
