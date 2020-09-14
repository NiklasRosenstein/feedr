
import time
import threading

from .model import session, session_context
from .model.task import Task


class TaskWorker(threading.Thread):

  def __init__(self, worker_id: str) -> None:
    super().__init__()
    self.__worker_id = worker_id
    self.__stop = False

  def stop(self):
    self.__stop = True

  def run(self):
    while not self.__stop:
      with session_context():
        task = Task.pending().first()
        if not task:
          time.sleep(0.1)
        else:
          task.execute(self.__worker_id)
