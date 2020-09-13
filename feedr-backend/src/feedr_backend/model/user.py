
from sqlalchemy import Column, Integer, String

from ._base import Entity, entity_retrieval_descriptor


class User(Entity):
  __tablename__ = __name__ + '.User'

  #: The unique ID of the user in this system.
  id = Column(Integer, primary_key=True)

  #: The unique user name of the user.
  user_name = Column(String, unique=True)

  #: The URL to the user's Avatar.
  avatar_url = Column(String, nullable=True)

  #: The ID of the collector where the user originates from.
  collector_id = Column(String)

  #: The foreign ID of the user in the collector's system.
  collector_key = Column(String)

  get = entity_retrieval_descriptor['User']()
