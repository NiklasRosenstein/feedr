
import json
import threading
import time
from databind.core import datamodel, field
from typing import Dict, List

from flask import Response, redirect, request

from feedr_oauth2 import OAuth2Session
from ._base import Component, route, register_component
from .session import SessionManager
from ..auth import AuthContext, AuthHandlerConfig, AuthHandler, LoginStateRecorder
from .. import model


@datamodel
class PendingLogin:
  session: OAuth2Session
  time_created: float = field(default_factory=time.time)


class AuthComponent(Component):

  def __init__(
    self,
    auth_handler_configs: Dict[str, AuthHandlerConfig],
    state_recorder: LoginStateRecorder,
    redirect_uri: str,
  ) -> None:

    self.auth_handlers = {
      k: v.get_auth_handler(AuthContext(k, state_recorder, redirect_uri))
      for k, v in auth_handler_configs.items()
    }
    self.state_recorder = state_recorder

  @route('/logout')
  def logout(self):
    self.state_recorder.logout()

  # Component

  def after_register(self, app, prefix):
    for auth_id, auth_handler in self.auth_handlers.items():
      register_component(auth_handler, app, prefix + '/' + auth_id)
