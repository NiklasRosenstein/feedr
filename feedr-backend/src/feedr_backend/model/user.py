
from sqlalchemy import Column, Binary, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ._base import Entity, entity_retrieval_descriptor


class User(Entity):
  __tablename__ = __name__ + '.User'

  #: The unique ID of the user in this system.
  id = Column(Integer, primary_key=True)

  #: The unique user name of the user.
  user_name = Column(String, unique=True)

  #: The URL to the user's Avatar URL (if available from an external service).
  avatar_url = Column(String, nullable=True)

  avatar = relationship('Avatar', back_populates='user', uselist=False)

  #: The ID of the collector where the user originates from.
  collector_id = Column(String)

  #: The foreign ID of the user in the collector's system.
  collector_key = Column(String)

  get = entity_retrieval_descriptor['User']()

  def save_avatar(self, raw_data: bytes, content_type: str) -> None:
    """
    Saves the avatar of the user.
    """

    if not content_type.startswith('image/'):
      raise ValueError(f'expected image content type, got {content_type!r}')

    self.avatar_url = None
    avatar = Avatar.get(
      on={'user_id': self.id},
      or_create={},
      and_update={'data': raw_data, 'content_type': content_type})


class Avatar(Entity):
  __tablename__ = __name__ + '.Avatar'

  user_id = Column(Integer, ForeignKey(User.id), primary_key=True)
  user = relationship(User, back_populates='avatar', uselist=False)
  data = Column(Binary, nullable=False)
  content_type = Column(String, nullable=False)

  get = entity_retrieval_descriptor['Avatar']()
