
import typing as t

_registrations: t.Dict[t.Hashable, 'Registration'] = {}
Registry = t.Dict[t.Hashable, t.List[t.Any]]


class Registration(t.NamedTuple):
  key: t.Hashable
  multiple: bool


def registration(key: t.Hashable, multiple: bool = False) -> None:
  if key in _registrations:
    raise RuntimeError(f'Registration for {key!r} already exists')
  _registrations[key] = Registration(key, multiple)


def registration_decorator(multiple: bool = False) -> t.Callable[[t.Hashable], t.Hashable]:
  def _decorator(key: t.Hashable) -> t.Hashable:
    registration(key, multiple)
    return key
  return _decorator


def get_registry(obj: t.Any, create: bool) -> t.Optional[Registry]:
  # We use vars() to avoid inheriting the property from a base if *obj* is a type object.
  registry = vars(obj).get('__addon_registry__')
  if registry is None and create:
    obj.__addon_registry__ = registry = {}
  return registry


def apply(obj: t.Any, key: t.Hashable, value: t.Any, multiple: bool = True) -> None:
  try:
    reg = _registrations[key]
  except KeyError as exc:
    raise RuntimeError(f'No Registration found for {key!r}. Did you call registration({key!r})?')

  if isinstance(key, type) and not isinstance(value, key):
    raise TypeError(f'The provided value is not a subclass of the Registration key {key!r}')

  registry = t.cast(Registry, get_registry(obj, True))
  container = registry.setdefault(key, [])
  if not reg.multiple and len(container) >= 1:
    raise
  container.append(value)


def get_all(obj: t.Any, key: t.Hashable) -> t.List[t.Any]:
  registry = get_registry(obj, False)
  if not registry:
    return []
  return registry.get(key, [])


def get_first(obj: t.Any, key: t.Hashable) -> t.Optional[t.Any]:
  container = get_all(obj, key)
  if container:
    return container[0]
  return None
