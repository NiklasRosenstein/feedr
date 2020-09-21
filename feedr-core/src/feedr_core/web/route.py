
import typing as t

from feedr_core.attach import register_attachment_type, attach


@register_attachment_type()
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

  def __init__(
    self,
    path: str,
    methods: t.Optional[t.List[str]] = None,
    success_code: int = 200,
  ) -> None:
    self.path = path
    self.methods = methods
    self.success_code = success_code
    self.func: t.Optional[t.Callable] = None
    self.endpoint_name: t.Optional[str] = None

  def __call__(self, method: t.Callable) -> t.Callable:
    """
    Decorate a method. This inserts the #Route object into the method using the
    #func.insert_addon() function and returns the method afterwards. The same method cannot
    be decorated with multiple routes.
    """

    attach(method, Route, self)
    self.func = method
    return method
