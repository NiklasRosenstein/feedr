
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


class Param:
  pass


@dataclass
class Query(Param):
  name: t.Optional[str] = None


@dataclass
class Header(Param):
  name: t.Optional[str] = None


class Body(Param):
  pass


@register_attachment_type()
class Parameters:
  """
  Decorator for declaring the source for additional route parameters that are not provided
  view the parameters defined in #Route.path.

  Example:

  ```python
  @Route('/users')
  @Parameters(query=Parameters.BODY)
  def get_users(self, query: UsersQuery) -> Users:
    ...
  ```
  """

  Query = Query
  Header = Header
  Body = Body

  def __init__(self, **params: t.Dict[str, Param]) -> None:
    self.params = params

  def __call__(self, method: t.Callable) -> t.Callable:
    for key in self.params:
      if key not in method.__annotations__:
        raise TypeError(f'{key!r} is not an annotated parameter of {method!r}')
    attach(method, Parameters, self)
    return method


@dataclass
class ErrorDescription:
  message: str
  parameters: t.Dict[str, t.Any]


def json_response(body: databind.json.JsonType, code: int, headers: t.Any) -> Response:
  # TODO: Serialize as a stream to avoid filling up memory for large responses?
  if isinstance(headers, t.Sequence):
    headers = dict(headers)
  headers['Content-Type'] = 'application/json'
  return flask.make_response(json.dumps(body), code, headers)


class JsonView(View):
  """
  This view subclass serializes respones from endpoints into JSON using the #databind.json
  module. Additional parameters, beyond the path parameters declared in the #@Route() decorator,
  be declared using the #@Parameters() decorator, which can then be de-serialized from the
  query string, headers or body.
  """

  def __init__(self, json_registry: t.Optional[databind.core.Registry] = None) -> None:
    super().__init__()
    self.json_registry = json_registry

  def abort(self, code: int, message: str, parameters: t.Dict[str, t.Any]) -> None:
    flask.abort(code, ErrorDescription(message, parameters))

  def process_route_kwargs(self, route: Route, kwargs: t.Dict[str, t.Any]) -> None:
    # TODO: Create a proper JSON response for missing parameters or parmaeters
    #       could not be de-serialized.
    parameters = t.cast(t.Optional[Parameters], retrieve(route.func, Parameters))
    if not parameters:
      return
    for name, source in parameters.params.items():
      annotated_type = route.func.__annotations__[name]
      if isinstance(source, Body):
        kwargs[name] = databind.json.from_json(
          annotated_type, flask.request.json, registry=self.json_registry
        )
      elif isinstance(source, (Query, Header)):
        origin = flask.request.args if isinstance(source, Query) else flask.request.headers
        value = t.cast(t.Mapping, origin).get(source.name or name)
        if value is not None and annotated_type is not str:
          value = json.loads(value)
        kwargs[name] = databind.json.from_json(
          annotated_type, t.cast(databind.json.JsonType, value), registry=self.json_registry
        )
      else:
        raise RuntimeError(f'Unexpected @Parameters() declaration: {name}={source!r}')

  def process_route_return(self, route: Route, return_: t.Any) -> t.Any:
    return_type = route.func.__annotations__['return']
    code = route.success_code
    headers = []

    if isinstance(return_, tuple):
      return_, code = return_[:2]
      if len(return_) > 2:
        headers = return_[2]

    payload = databind.json.to_json(return_, return_type, registry=self.json_registry)
    return json_response(payload, code, headers)

  def handle_route_exception(self, route: Route, exc: BaseException) -> t.Optional[Response]:
    # TODO: In debug mode, include stacktrace.
    if isinstance(exc, werkzeug.exceptions.HTTPException):
      if isinstance(exc.description, str):
        description = ErrorDescription(exc.description, {})
      elif isinstance(exc.description, t.Mapping):
        description = ErrorDescription(type(exc).description, exc.description)
      elif isinstance(exc.description, ErrorDescription):
        description = exc.description
      else:
        description = ErrorDescription(str(exc.description), {})
      payload = {
        'errorName': exc.name,
        'message': description.message,
        'parameters': description.parameters,
      }
      status_code = t.cast(int, exc.code)
    else:
      payload = {
        'errorName': 'Internal Server Error',
        'message': 'An unexpected internal error occurred.',
        'parameters': {},
      }
      status_code = 500
    return json_response(payload, status_code, [])
