
from functools import partial
from typing import Any, Dict, Generic, Optional, Type, TypeVar, TYPE_CHECKING
if TYPE_CHECKING:
  from typing import Protocol

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import and_

Entity = declarative_base()
T_Entity = TypeVar('T_Entity', bound=Entity)


if TYPE_CHECKING:
  class _BoundEntityRetrieval(Protocol):
    def __call__(self,
      on: Dict[str, Any],
      then_update: Optional[Dict[str, Any]] = None,
      or_create: Optional[Dict[str, Any]] = None,
      and_update: Optional[Dict[str, Any]] = None,
    ):
      ...


def _unbound_entity_retrieval(
  session: Session,
  entity_cls: Type[T_Entity],
  on: Dict[str, Any],
  then_update: Optional[Dict[str, Any]] = None,
  or_create: Optional[Dict[str, Any]] = None,
  or_none: bool = False,
  and_update: Optional[Dict[str, Any]] = None,
) -> T_Entity:

  filters = and_(*(getattr(entity_cls, k) == v for k, v in on.items()))
  query = session.query(entity_cls).filter(filters)

  try:
    instance = query.one()
  except NoResultFound:
    if or_create is not None:
      instance = entity_cls(**on, **or_create)  # type: ignore
      session.add(instance)
    else:
      raise
  else:
    if then_update is not None:
      for key, value in then_update.items():
        setattr(instance, key, value)
      session.add(instance)

  if instance is not None:
    if and_update is not None:
      for key, value in and_update.items():
        setattr(instance, key, value)
      session.add(instance)

  return instance


class entity_retrieval_descriptor(Generic[T_Entity]):
  """
  A descriptor that can be declared on the class-level of an entity to bind the
  #entity_retrieval() method to the entity.

  Example:

  ```py
  class User(Entity):
    id = Column(Integer)
    name = Column(String)
    get = entity_retrieval_descriptor['User']()

  user = User.get(on={'id': 42}, or_create={'name': 'Mr. Universal'})
  """

  def __get__(self,
    obj: Optional[T_Entity],
    type_: Optional[Type[T_Entity]] = None,
  ) -> '_BoundEntityRetrieval':
    from ._session import session
    assert type_ is not None
    return partial(_unbound_entity_retrieval, session, type_)
