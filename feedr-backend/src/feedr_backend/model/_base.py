
from functools import partial
from typing import Any, Dict, Generic, Optional, Type, TypeVar, TYPE_CHECKING
if TYPE_CHECKING:
  from typing import Protocol

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import and_

Entity = declarative_base()
T = TypeVar('T')
T_Entity = TypeVar('T_Entity', bound=Entity)


class _RetrievalHelper(Generic[T_Entity]):
  """
  A helper class that allows you to write SqlAlchemy queries for retrieving, creating and/or
  updating a row using a builder pattern.
  """

  def __init__(self, session: Session, entity_cls: T_Entity, on: Any) -> None:
    self._session = session
    self._entity_cls = entity_cls
    self._on = on

  def _get(self) -> T_Entity:
    filters = and_(*(getattr(self._entity_cls, k) == v for k, v in self._on.items()))
    query = self._session.query(self._entity_cls).filter(filters)
    return query.one()

  @property
  def instance(self) -> T_Entity:
    return self._get()

  def or_create(self, **values: Any) -> T_Entity:
    try:
      return self._get()
    except NoResultFound:
      instance = self._entity_cls(**self._on, **values)  # type: ignore
      self._session.add(instance)
      return instance

  def or_none(self) -> Optional[T_Entity]:
    try:
      return self._get()
    except NoResultFound:
      return None

  def then_update(self, **values: Any) -> T_Entity:
    instance = self._get()
    for key, value in values.items():
      setattr(instance, key, value)
    self._session.add(instance)
    return instance

  def create_or_update(self, **values: Any) -> T_Entity:
    try:
      instance = self._get()
    except NoResultFound:
      instance = self._entity_cls(**self._on, **values)  # type: ignore
    else:
      for key, value in values.items():
        setattr(instance, key, value)
    self._session.add(instance)
    return instance


class instance_getter(Generic[T_Entity]):
  """
  Example:

  ```py
  class User(Entity):
    id = Column(Integer)
    name = Column(String)
    get = instance_getter['User']()

  user = User.get(id=42).or_create(name='Mr. Universal')
  """

  if TYPE_CHECKING:
    class _GetProto(Protocol[T]):
      def __call__(self, **on: Any) -> _RetrievalHelper[T]:
        ...

  def __get__(self,
    obj: Optional[T_Entity],
    type_: Optional[Type[T_Entity]] = None,
  ) -> '_GetProto[T_Entity]':
    from ._session import session
    assert type_ is not None
    def getter(**on):
      return _RetrievalHelper[T_Entity](session, type_, on)
    return getter
