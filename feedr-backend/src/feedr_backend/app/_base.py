
import functools
import types
from typing import Callable, Optional, Union, cast

import flask
from databind.json import to_str

FlaskTarget = Union[flask.Flask, flask.Blueprint]


def route(rule: str, **options) -> Callable[[Callable], Callable]:
  """
  A route decorator for methods on a #Component subclass. A component can be registered to a
  #flask.Flask or #flask.Blueprint object at a later point in time using the #register_component()
  function.
  """

  def decorator(func: Callable) -> Callable:
    func.__route__ = (rule, options)  # type: ignore
    return func

  return decorator


def register_component(
  component: 'Component',
  app: FlaskTarget,
  prefix: Optional[str] = None,
) -> None:
  """
  Registers all endpoints associated with a component.
  """

  fqn = f'{type(component).__module__}.{type(component).__name__}'

  component.before_register(app, prefix)

  for member_name in dir(type(component)):
    value = getattr(type(component), member_name)
    if not isinstance(value, types.FunctionType):
      continue
    if not hasattr(value, '__route__'):
      continue
    rule, options = value.__route__  # type: ignore
    if prefix:
      rule = prefix + rule
    if 'endpoint' not in options:
      options = dict(options)
      options['endpoint'] = f'{fqn}.{member_name}'
    app.add_url_rule(rule, view_func=functools.partial(value, component),**options)

  if component.before_request != Component.before_request:
    app.before_request(component.before_request)
  if component.after_request != Component.after_request:
    app.after_request(component.after_request)
  if component.teardown_request != Component.teardown_request:
    app.teardown_request(component.teardown_request)

  component.after_register(app, prefix)


def url_for(endpoint: Union[str, Callable], **kwargs) -> str:
  """
  Similar to #flask.url_for(), but accepts an instance method.
  """

  if not isinstance(endpoint, str):
    endpoint = cast(str, endpoint.__route__[1]['endpoint'])  # type: ignore
  return flask.url_for(endpoint, **kwargs)


class Component:

  def before_register(self, app: FlaskTarget, prefix: str) -> None:
    pass

  def after_register(self, app: FlaskTarget, prefix: str) -> None:
    pass

  def before_request(self) -> Optional[flask.Request]:
    return None

  def after_request(self, response: flask.Response) -> flask.Response:
    return response

  def teardown_request(self, error: Optional[Exception]) -> None:
    pass


def json_response(func):
  """
  Decorator for a function that returns an object that is serializing with #databind.json.
  The return type must be annotated in the function.
  """

  return_type = func.__annotations__['return']

  @functools.wraps(func)
  def wrapper(*args, **kwargs):
    return (to_str(func(*args, **kwargs), return_type), 200, [('Content-Type', 'application/json')])

  return wrapper
