
"""
Attach arbitary data to functions and classes.

# Example

```python
from feedr_core.attach import register_attachment_type, attach, retrieve

@register_attachment_type(multiple=False)
class MyAttachment:
  def __init__(self, value: int) -> None:
    self.value = value

def my_function():
  pass

attach(my_function, MyAttachment, MyAttachment(42))
attachment: MyAttachment = retrieve(my_function, MyAttachment)
assert attachment.value == 42
```

> __Implementation Detail__: The data is attached on the object via the `__attachment_registry__`
> parameter. The object must support dunder-attribute assignment to create the attribute if it
> does not already exist.
"""

import types
import typing as t

_metadata: t.Dict[t.Type, 'Metadata'] = {}
Registry = t.Dict[t.Type, t.List[t.Any]]
T = t.TypeVar('T')
ATTACHMENT_REGISTRY_ATTR = '__attachment_registry__'


def _get_registry(obj: t.Any) -> t.Optional[Registry]:
  # We use vars() to avoid inheriting the property from a base if *obj* is a type object.
  return vars(obj).get(ATTACHMENT_REGISTRY_ATTR)


def _ensure_registry(obj: t.Any) -> Registry:
  registry = _get_registry(obj)
  if registry is None:
    registry = {}
    setattr(obj, ATTACHMENT_REGISTRY_ATTR, registry)
  return registry


class Metadata(t.NamedTuple):
  """
  Represents the metadata that must be registered for an attachment type. Note that a type can
  only be used as a key to attach data on an object if it has metadata registered.
  """

  type: t.Type
  multiple: bool


@t.overload
def register_attachment_type(type_: t.Type, multiple: bool = False) -> None:
  pass


@t.overload
def register_attachment_type(*, multiple: bool = False) -> t.Callable[[t.Type], t.Type]:
  pass


def register_attachment_type(type_=None, multiple=False):
  """
  Register a type so that it can be used as a key to attach data to a Python object.
  """

  if type_ is None:
    def _decorator(type_):
      assert type_ is not None
      register_attachment_type(type_)
      return type_
    return _decorator

  if type_ in _metadata:
    raise RuntimeError(f'Registration for {type_!r} already exists')

  _metadata[type_] = Metadata(type_, multiple)


class MultipleAttachmentsNotAllowed(Exception):
  pass


def attach(obj: t.Any, type_: t.Type[T], value: T, multiple: bool = True) -> None:
  """
  For a registered attachment type *type_*, attach an instance of the type *value* to the
  object *obj*. If a value for the attachment type already exists on the object and the
  attachment type does not permit multiple values, a #MultipleAttachmentsNotAllowed exception
  is raised.

  If the *type_* is not a registered attachment type, a #RuntimeError will be raised.
  """

  try:
    reg = _metadata[type_]
  except KeyError as exc:
    raise RuntimeError(f'No Registration found for {type_!r}. Did you call registration({type_!r})?')

  if isinstance(type_, type) and not isinstance(value, type_):
    raise TypeError(f'The provided value is not a subclass of key {type_!r}')

  registry = _ensure_registry(obj)
  container = registry.setdefault(type_, [])
  if not reg.multiple and len(container) >= 1:
    raise MultipleAttachmentsNotAllowed()
  container.append(value)


def retrieve(obj: t.Any, type_: t.Type[T], include_bases: bool = True) -> t.Optional[T]:
  """
  Retrieve a single value of the attachment type *type_* from the object *obj*.
  """

  return next(retrieve_all(obj, type_, include_bases), None)


def retrieve_all(obj: t.Any, type_: t.Type[T], include_bases: bool = True) -> t.Iterable[T]:
  """
  Retrieve a list of all values registered to *obj* for the attachment type *type_*.
  """

  if isinstance(obj, types.MethodType):
    obj = obj.__func__

  registry = _get_registry(obj)
  if registry:
    yield from registry.get(type_, [])

  if include_bases and isinstance(obj, type):
    for base in obj.__bases__:
      yield from retrieve_all(base, type_, True)
