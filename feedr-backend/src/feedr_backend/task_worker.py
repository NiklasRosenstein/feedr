
import functools
import heapq
import logging
import time
import threading
from typing import Callable, List, Tuple

from .model import session, session_context
from .model.task import Task

logger = logging.getLogger(__name__)


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


class BackgroundDispatcher(threading.Thread):

  def __init__(self) -> None:
    super().__init__()
    self.__heap: List[Tuple[float, Callable[[], None]]] = []
    self.__lock = threading.Lock()
    self.__cond = threading.Condition(self.__lock)
    self.__stop = False

  def stop(self):
    with self.__cond:
      self.__stop = True
      self.__cond.notify()

  def push(self, run_at: float, callback: Callable[[], None]) -> None:
    with self.__cond:
      heapq.heappush(self.__heap, (run_at, callback))
      self.__cond.notify()

  def push_recurring(self, interval: float, callback: Callable[[], None]) -> None:
    @functools.wraps(callback)
    def _callback():
      try:
        callback()
      finally:
        self.push(time.time() + interval, _callback)
    self.push(time.time(), _callback)

  def run(self):
    while True:
      with self.__cond:
        if not self.__heap:
          self.__cond.wait()
        if self.__stop:
          break
        if not self.__heap:
          continue
        t, callback = heapq.heappop(self.__heap)
      if t <= time.time():
        try:
          logger.info('Calling %s', callback)
          callback()
        except:
          logger.exception('Error in background dispatcher')
      else:
        self.push(t, callback)
