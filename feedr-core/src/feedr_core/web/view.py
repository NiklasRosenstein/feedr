
import sys
import types
import typing as t

import flask
from nr.metaclass.inline import InlineMetaclass
from werkzeug.wrappers.response import Response

from feedr_core import addon
from feedr_core.web.route import Route


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
      route = t.cast(t.Optional[Route], addon.get_first(value, Route))
      if not route:
        continue
      self.__routes__[key] = route

  def __init__(self) -> None:
    # These are set when registered to an application.
    self.parent: t.Optional['View'] = None
    self.prefix: str = ''
    self.app: t.Optional[flask.Flask] = None
    self.children: t.List[View] = []

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

    self.app = flask
    for child in self.children:
      child.bind(flask, prefix + self.prefix)

    cls = type(self)
    for name, route in self.__routes__.items():
      route.endpoint_name = f'{prefix}{self.prefix}:{cls.__module__}.{cls.__name__}:{name}'
      flask.add_url_rule(
        rule=prefix + self.prefix + route.path,
        methods=route.methods,
        endpoint=route.endpoint_name,
        view_func=EndpointWrapper(self, route),
      )

  def url_for(self, route_name: str, **kwargs) -> str:
    route = self.__routes__[route_name]
    assert route.endpoint_name
    return flask.url_for(route.endpoint_name, **kwargs)

  def process_route_kwargs(self, route: Route, kwargs: t.Dict[str, t.Any]) -> None:
    ...

  def process_route_return(self, route: Route, return_: t.Any) -> t.Any:
    return return_

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
    finally:
      for view in self.view.upiter():
        view.teardown_request(sys.exc_info()[1])
    return response
