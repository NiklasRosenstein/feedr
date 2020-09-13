
import json
import threading
import time
from databind.core import datamodel, field
from typing import Dict, List

from flask import Response, redirect, request

from feedr_oauth2 import OAuth2Session
from ._base import Component, route
from ..auth import AuthPlugin


@datamodel
class PendingLogin:
  session: OAuth2Session
  time_created: float = field(default_factory=time.time)


class AuthComponent(Component):

  def __init__(self,
    collectors: Dict[str, AuthPlugin],
    max_login_state_age: int = 60,
  ) -> None:
    self.collectors = collectors
    self.max_login_state_age = max_login_state_age
    self._pending_logins: List[PendingLogin] = []
    self.lock = threading.Lock()

  def _push_pending_login(self, session: OAuth2Session) -> None:
    with self.lock:
      self._drop_pending_logins()
      self._pending_logins.append(PendingLogin(session))

  def _find_pending_login(self, state: str) -> OAuth2Session:
    with self.lock:
      self._drop_pending_logins()
      for index, pending_login in enumerate(self._pending_logins):
        if pending_login.session.state == state:
          break
      else:
        raise RuntimeError(f'state {state!r} doesnt exist')
      del self._pending_logins[index]
      return pending_login.session

  def _drop_pending_logins(self) -> None:
    assert self.lock.locked()
    ctime = time.time()
    self._pending_logins[:] = (s for s in self._pending_logins
      if (ctime - s.time_created) < self.max_login_state_age)

  @route('/collector/<collector_id>/login')
  def begin_login(self, collector_id: str):
    session = self.collectors[collector_id].create_login_session()
    self._push_pending_login(session)
    return redirect(session.login_url)

  @route('/collector/<collector_id>/authorized')
  def collect(self, collector_id: str):
    session = self._find_pending_login(request.args['state'])
    access_data = session.get_token(request.args['code'])
    collector = self.collectors[collector_id]
    user = collector.finalize_login(access_data)
    return f'Hello {user.user_name}'
