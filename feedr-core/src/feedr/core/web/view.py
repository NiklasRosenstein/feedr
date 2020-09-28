
import sys
import types
import typing as t

import flask
from nr.metaclass.inline import InlineMetaclass
from werkzeug.wrappers.response import Response

from .attach import retrieve
from .route import Route, Query, Header, Body, Parameters
from .serde import get_serde


class View(metaclass=InlineMetaclass):
  """
  A #View represents a pluggable collection of endpoints that can be registered to a Flask
  application. Methods on a #View must be decorated with the #Route class to register them
  as endpoints.

  Views can have sub-views attached to them. Sub-views need to be registered on a view before
  the view is registered to an application.
  """

  __routes__: t.Dict[str, Route]

  def __metainit__(self, name, bases, data):
    # Inherit parent class routes.
    self.__routes__ = dict(getattr(self, '__routes__', {}))

    for key, value in vars(self).items():
      if not isinstance(value, types.FunctionType):
        continue
      route = retrieve(value, Route)
      if not route:
        continue
      self.__routes__[key] = route

  def __init__(self) -> None:
    # These are set when registered to an application.
    self.parent: t.Optional['View'] = None
    self.prefix: str = ''
    self.app: t.Optional[flask.Flask] = None
    self.children: t.List[View] = []

  def _get_content_type(self, route: Route) -> t.Optional[str]:
    if route.content_type is not NotImplemented:
      return route.content_type
    view_route = retrieve(self.__class__, Route)
    if view_route and view_route.content_type is not NotImplemented:
      return view_route.content_type
    return None

  def upiter(self) -> t.Iterable['View']:
    view: t.Optional[View] = self
    while view:
      yield view
      view = view.parent

  def register_view(self, view: 'View', prefix: str = '') -> None:
    """
    Registers a sub-view.
    """

    if self.app or view.app:
      raise RuntimeError(f'View {self if self.app else view!r} is already bound to an application')

    if view.parent:
      raise RuntimeError(f'View {view!r} already has a parent')

    view.prefix = prefix
    view.parent = self
    self.children.append(view)

  def bind(self, flask: flask.Flask, prefix: str = '') -> None:
    """
    Bind the view and it's sub-views to the Flask application under the specified prefix. This
    should only be called once for a root view.
    """

    if self.app:
      raise RuntimeError(f'View {self!r} is already bound to a Flask application')

    prefix = prefix + self.prefix

    view_route = retrieve(self.__class__, Route)
    if view_route and view_route.path:
      prefix += view_route.path

    self.app = flask
    for child in self.children:
      child.bind(flask, prefix)

    cls = type(self)
    for name, route in self.__routes__.items():
      assert route.path
      route.endpoint_name = f'{prefix}:{cls.__module__}.{cls.__name__}:{name}'
      flask.add_url_rule(
        rule=prefix + route.path,
        methods=route.methods,
        endpoint=route.endpoint_name,
        view_func=EndpointWrapper(self, route),
      )

  def url_for(self, route_name: str, **kwargs) -> str:
    route = self.__routes__[route_name]
    assert route.endpoint_name
    return flask.url_for(route.endpoint_name, **kwargs)

  def process_route_kwargs(self, route: Route, kwargs: t.Dict[str, t.Any]) -> None:
    assert self.app is not None

    content_type = self._get_content_type(route)
    if content_type is None:
      return

    parameters = retrieve(route.func, Parameters)
    if not parameters:
      return

    serde = get_serde(self.app, content_type)

    for name, source in parameters.params.items():
      annotated_type = route.func.__annotations__[name]
      if isinstance(source, Body):
        kwargs[name] = serde.read_body(flask.request, annotated_type)
      elif isinstance(source, Query):
        kwargs[name] = serde.read_query(flask.request, annotated_type)
      elif isinstance(source, Header):
        kwargs[name] = serde.read_header(flask.request, annotated_type)
      else:
        raise RuntimeError(f'Unexpected @JsonParameters() declaration: {name}={source!r}')

  def process_route_return(self, route: Route, result: t.Any) -> t.Any:
    assert self.app is not None

    if 'return' not in route.func.__annotations__:
      return result
    return_type = route.func.__annotations__['return']

    content_type = self._get_content_type(route)
    if content_type is None:
      return result

    code = route.success_code
    headers = []

    # Unpack the view return value.
    if isinstance(result, tuple):
      result, code = result[:2]
      if len(result) > 2:
        headers = result[2]

    serde = get_serde(self.app, content_type)
    return serde.write(return_type, result, code, headers)

  def handle_route_exception(self, route: Route, exc: BaseException) -> t.Optional[Response]:
    return None

  def before_request(self) -> t.Optional[Response]:
    return None

  def after_request(self, response: Response) -> Response:
    return response

  def teardown_request(self, error: t.Optional[BaseException]) -> None:
    ...


class EndpointWrapper:

  def __init__(self, view: View, route: Route) -> None:
    self.view = view
    self.route = route

  def __call__(self, **kwargs) -> t.Any:
    assert self.route.func
    self.view.process_route_kwargs(self.route, kwargs)
    try:
      for view in self.view.upiter():
        response = view.before_request()
        if response is not None:
          return response
      result = self.route.func(self.view, **kwargs)
      result = self.view.process_route_return(self.route, result)
      response = flask.make_response(result)
      for view in self.view.upiter():
        response = self.view.after_request(response)
    except BaseException as exc:
      response = self.view.handle_route_exception(self.route, exc)
      if response is None:
        raise
    finally:
      for view in self.view.upiter():
        view.teardown_request(sys.exc_info()[1])
    return response
