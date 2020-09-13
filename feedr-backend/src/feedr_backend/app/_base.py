
import types
from typing import Callable, Optional, Union

import flask

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

  for member_name in dir(component):
    value = getattr(component, member_name)
    if not isinstance(value, (types.MethodType, types.FunctionType)):
      continue
    if not hasattr(value, '__route__'):
      continue
    rule, options = value.__route__  # type: ignore
    if prefix:
      rule = prefix + rule
    if 'endpoint' not in options:
      options['endpoint'] = f'{fqn}.{member_name}'
    app.add_url_rule(rule, view_func=value,**options)


class Component:
  pass
