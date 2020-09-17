
import enum
import json
import typing as t

import databind.json
import flask
from feedr_core import addon
from feedr_core.web.route import Route
from feedr_core.web.view import View


class Param:
  pass


class Query(Param, t.NamedTuple):
  name: t.Optional[str] = None


class Header(Param, t.NamedTuple):
  name: t.Optional[str] = None


class Body(Param):
  pass


@addon.registration_decorator(multiple=False)
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
    addon.apply(method, Parameters, self)
    return method


class JsonView(View):
  """
  This view subclass serializes respones from endpoints into JSON using the #databind.json
  module. Additional parameters, beyond the path parameters declared in the #@Route() decorator,
  be declared using the #@Parameters() decorator, which can then be de-serialized from the
  query string, headers or body.
  """

  def process_route_kwargs(self, route: Route, kwargs: t.Dict[str, t.Any]) -> None:
    # TODO: Create a proper JSON response for missing parameters or parmaeters
    #       could not be de-serialized.
    parameters = t.cast(t.Optional[Parameters], addon.get_first(route.func, Parameters))
    if not parameters:
      return
    for name, source in parameters.params.items():
      annotated_type = route.func.__annotations__[name]
      if isinstance(source, Body):
        kwargs[name] = databind.json.from_json(annotated_type, flask.request.json)
      elif isinstance(source, (Query, Header)):
        origin = flask.request.args if isinstance(source, Query) else flask.request.headers
        value = origin.get(source.name or name)
        if value is not None and annotated_type is not str:
          value = json.loads(value)
        kwargs[name] = databind.json.from_json(annotated_type, value)
      else:
        raise RuntimeError(f'Unexpected @Parameters() declaration: {name}={source!r}')

  def process_route_return(self, route: Route, return_: t.Any) -> t.Any:
    return_type = route.func.__annotations__['return']
    return databind.json.to_json(return_, return_type)

  # TODO: Translate exceptions in the route func to JSON responses.
