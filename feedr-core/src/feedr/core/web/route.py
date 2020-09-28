
import typing as t
from dataclasses import dataclass
from .attach import register_attachment_type, attach


@register_attachment_type()
@dataclass
class Route:
  """
  A route describes endpoint metadata, e.g. it's path and the HTTP method(s) that it is
  compatible with. The route path must be compatible with werkzeug's route syntax (as you
  would also use it in Flask).

  Route instances decorate methods on #View subclasses.

  The endpoint name for routes is derived from the prefix that the view is mounted on
  in the application and the fully qualified name of the view's method (using the class and
  function name).
  """

  path: t.Optional[str] = None
  methods: t.Optional[t.List[str]] = None
  success_code: int = 200
  content_type: t.Union[str, None, NotImplemented.__class__] = NotImplemented
  func: t.Optional[t.Callable] = None
  endpoint_name: t.Optional[str] = None

  def __call__(self, method: t.Callable) -> t.Callable:
    """
    Decorate a method. This inserts the #Route object into the method using the
    #func.insert_addon() function and returns the method afterwards. The same method cannot
    be decorated with multiple routes.
    """

    attach(method, Route, self)
    self.func = method
    return method


@dataclass
class Param:
  pass


class Body(Param):
  content_type: t.Optional[str] = None


@dataclass
class Header(Param):
  name: t.Optional[str] = None
  content_type: t.Optional[str] = None


@dataclass
class Query(Param):
  name: t.Optional[str] = None
  content_type: t.Optional[str] = None


@register_attachment_type()
class Parameters:
  """
  Decorator for declaring the source for additional route parameters that are not provided
  view the parameters defined in #Route.path.

  Example:

  ```python
  @Route('/users')
  @Parameters(query=Parameters.Body())
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
