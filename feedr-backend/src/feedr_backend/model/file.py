
import abc
import contextlib
import logging
import uuid
from pathlib import Path
from typing import BinaryIO, Iterator, Optional, Tuple, Union, cast

import nr.proxy
from sqlalchemy import Column, Integer, String, event

from ._base import Entity
from ._session import session

logger = logging.getLogger(__name__)
storage: 'StorageManager' = nr.proxy.proxy['LocalStorageManager']()  # type: ignore


class StorageManager(metaclass=abc.ABCMeta):
  """
  Abstract base class for storage managers.
  """

  @abc.abstractmethod
  def create(self) -> Tuple[BinaryIO, str]:
    """
    Create a new file and return a tuple of the writable file object and the file ID.
    """

  @abc.abstractmethod
  def open(self, file_id: str) -> BinaryIO:
    """
    Open a file by file ID for reading.
    """

  @abc.abstractmethod
  def delete(self, file_id: str) -> None:
    """
    Delete a file by file ID.
    """


class LocalStorageManager(StorageManager):

  def __init__(self, directory: Union[Path, str]) -> None:
    self._directory = Path(directory)

  def _file_id_to_path(self, file_id: str) -> Path:
    return self._directory / file_id[0:2] / file_id[2:4] / file_id[4:]

  def create(self) -> Tuple[BinaryIO, str]:
    file_id = str(uuid.uuid4())
    path = self._file_id_to_path(file_id)
    path.parent.mkdir(exist_ok=True, parents=True)
    return path.open('wb'), file_id

  def open(self, file_id: str) -> BinaryIO:
    return self._file_id_to_path(file_id).open('rb')

  def delete(self, file_id: str):
    try:
      self._file_id_to_path(file_id).unlink()
    except OSError as exc:
      logger.warning('Unable to delete file "%s" from disk: %s', file_id, exc)


class File(Entity):
  """
  Represents a file on disk.
  """

  __tablename__ = __name__ + '.File'

  id = Column(Integer, primary_key=True)

  #: ID of the file as represented by the storage manager. Usually this is just a relative
  #: path to the file from a root data directory.
  file_id = Column(String, nullable=False)

  #: An optional filename.
  filename = Column(String, nullable=True)

  #: The mimetype of the file.
  mimetype = Column(String, nullable=True)

  #: Some value to indicate the state of the file (e.g. a hash).
  state = Column(String, nullable=True)

  @classmethod
  @contextlib.contextmanager
  def create(cls,
    filename: Optional[str] = None,
    mimetype: Optional[str] = None,
    state: Optional[str] = None,
  ) -> Iterator[Tuple[BinaryIO, 'File']]:
    fp, file_id = storage.create()
    try:
      try:
        instance = cls(file_id=file_id, filename=filename, mimetype=mimetype, state=state)
        yield fp, instance
      finally:
        if not fp.closed:
          fp.close()
    except:
      storage.delete(file_id)
      raise
    else:
      session.add(instance)

  def open(self) -> BinaryIO:
    return storage.open(self.file_id)


@event.listens_for(File, 'after_delete')
def _file_after_delete(mapper, connection, target: File):
  logger.info('Deleting file "%s" from disk', target.file_id)
  storage.delete(target.file_id)


def init_storage(storage_manager: StorageManager) -> None:
  nr.proxy.set_value(cast(nr.proxy.proxy, storage), storage_manager)
