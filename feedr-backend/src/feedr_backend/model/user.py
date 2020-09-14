
import datetime
import uuid
from typing import Optional

from sqlalchemy import Column, Binary, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from ._base import Entity, instance_getter
from ._session import session
from .file import File


class User(Entity):
  __tablename__ = __name__ + '.User'

  #: The unique ID of the user in this system.
  id = Column(Integer, primary_key=True)

  #: The unique user name of the user.
  user_name = Column(String, unique=True)

  #: The URL to the user's Avatar URL (if available from an external service).
  avatar_url = Column(String, nullable=True)

  #: A reference to a file that stores the user's avatar. This is only used in cases
  #: where there is no #avatar_url and the image is stored directlry.
  avatar_file_id = Column(Integer, ForeignKey(File.id))

  #: The ID of the collector where the user originates from.
  collector_id = Column(String)

  #: The foreign ID of the user in the collector's system.
  collector_key = Column(String)

  avatar_file = relationship(File, backref=None, uselist=False)
  tokens = relationship('Token', back_populates='user')
  get = instance_getter['User']()

  def save_avatar(self, raw_data: bytes, content_type: str) -> None:
    """
    Saves the avatar of the user.
    """

    if not content_type.startswith('image/'):
      raise ValueError(f'expected image content type, got {content_type!r}')

    self.avatar_url = None
    if self.avatar_file:
      session.delete(self.avatar_file)
    with File.create(mimetype=content_type) as (fp, file_):
      fp.write(raw_data)
      self.avatar_file = file_

  def create_token(self, expiration_date: datetime.datetime) -> 'Token':
    token = Token(user=self, value=str(uuid.uuid4()), expiration_date=expiration_date)
    session.add(token)
    return token


class Token(Entity):
  __tablename__ = __name__ + '.Token'

  id = Column(Integer, primary_key=True)
  user_id = Column(Integer, ForeignKey(User.id))
  user = relationship(User, back_populates='tokens', uselist=False)
  value = Column(String, unique=True, nullable=False)
  expiration_date = Column(DateTime, nullable=False)
  revoked_at = Column(DateTime, nullable=True)

  get = instance_getter['Token']()

  @property
  def is_valid(self) -> bool:
    return not self.is_revoked and not self.is_expired

  @property
  def is_revoked(self) -> bool:
    return self.revoked_at is not None

  @property
  def is_expired(self) -> bool:
    return datetime.datetime.utcnow() >= self.expiration_date

  def revoke(self) -> None:
    self.revoked_at = datetime.datetime.utcnow()


class LoginState(Entity):
  __tablename__ = __name__ + '.LoginState'

  id = Column(String, primary_key=True)
  expires_at = Column(DateTime, nullable=False)
  data = Column(JSON, nullable=False)

  get = instance_getter['LoginState']()

  @property
  def is_expired(self) -> bool:
    return datetime.datetime.utcnow() >= self.expires_at
