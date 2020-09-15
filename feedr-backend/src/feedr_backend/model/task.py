
import abc
import enum
import datetime
import importlib
import logging
import sys
from typing import Optional

from databind.json import from_json, to_json
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, JSON, String, desc, event
from sqlalchemy.orm.query import Query

from ._base import Entity
from ._session import Session, session, session_context
from .file import File

logger = logging.getLogger(__name__)


class BaseTask(metaclass=abc.ABCMeta):

  def execute(self):
    pass


class TaskStatus(enum.Enum):
  PENDING = enum.auto()
  IN_PROGRESS = enum.auto()
  COMPLETED = enum.auto()
  FAILED = enum.auto()


class Task(Entity):
  """
  Represents a generic task that can be executed as soon as it hit's the front of the queue.
  Tasks are used in the background only and are not exposed to users.
  """

  __tablename__ = __name__ + '.Task'

  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False)
  origin = Column(String, nullable=False)
  class_name = Column(String, nullable=False)
  args = Column(JSON, nullable=False)
  created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
  status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
  worker_id = Column(String, nullable=True, default=None)
  started_at = Column(DateTime, nullable=True, default=None)
  ended_at = Column(DateTime, nullable=True, default=None)
  log_file = Column(Integer, ForeignKey(File.id), nullable=True, default=None)

  def __repr__(self):
    return f'Task(id={self.id!r}, status={self.status.name!r}, name={self.name!r}, '\
           f'class_name={self.class_name!r})'

  @classmethod
  def pending(cls) -> Query:
    return session.query(cls).filter(cls.status == TaskStatus.PENDING).order_by(desc(cls.id))

  @classmethod
  def create(cls, name: str, origin: str, task_impl: BaseTask) -> 'Task':
    class_name = type(task_impl).__module__ + ':' + type(task_impl).__name__
    args = to_json(task_impl, type(task_impl))
    task = cls(name=name, origin=origin, class_name=class_name, args=args)
    return task

  def load(self) -> BaseTask:
    module_name, member_name = self.class_name.split(':')
    module = importlib.import_module(module_name)
    type_ = getattr(module, member_name)
    return from_json(type_, self.args)

  def execute(self, worker_id: str):
    assert self.status == TaskStatus.PENDING
    self.worker_id = worker_id
    self.status = TaskStatus.IN_PROGRESS
    self.started_at = datetime.datetime.utcnow()
    session.commit()

    logger.info('Executing task %s', self)
    try:
      # TODO: Execute in separate process to capture full stdout/stderr.
      #with session_context():
      impl = self.load()
      impl.execute()
    except BaseException as exc:
      logger.exception('Error executing task %s', self)
      status = TaskStatus.FAILED
    else:
      status = TaskStatus.COMPLETED

    self.ended_at = datetime.datetime.utcnow()
    self.status = status
    #self.log_file = ...
    session.commit()
    logger.info('Completed execution of task %s', self)


@event.listens_for(Task, 'after_insert')
def _task_saved(mapper, connection, target: Task):
  logger.info('Queued task (id: %d, name: %r, origin: %r, class_name: %r)',
    target.id, target.name, target.origin, target.class_name)


def queue_task(name: str, task_impl: BaseTask, stackdepth: int = 1) -> Task:
  assert isinstance(task_impl, BaseTask), 'expected BaseTask instance'
  frame = sys._getframe(stackdepth)
  try:
    origin = frame.f_code.co_filename + ':' + str(frame.f_lineno)
  finally:
    del frame
  task = Task.create(name, origin, task_impl)
  session.add(task)
  session.commit()
  logger.info('Queued task %s', task)
  return task
