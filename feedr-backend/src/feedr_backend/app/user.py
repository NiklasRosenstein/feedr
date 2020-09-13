
import io
from typing import Optional

import requests
from databind.core import datamodel
from flask import abort, send_file

from ._base import Component, route, url_for, json_response
from .session import SessionManager
from ..model.user import User


@datamodel
class UserInfo:
  id: int
  user_name: str
  avatar_url: Optional[str]


class UserComponent(Component):

  def __init__(self, session_manager: SessionManager) -> None:
    self._session_manager = session_manager

  @route('/me')
  def get_me(self) -> UserInfo:
    user = self._session_manager.current_user
    if not user:
      abort(403)
    return self.get_user(user.id)

  @route('/<int:user_id>')
  @json_response
  def get_user(self, user_id: int) -> UserInfo:
    if not self._session_manager.current_user:
      abort(403)
    user = User.get(id=user_id).instance
    if user.avatar:
      avatar_url = url_for(self.get_avatar, user_id=user_id)
    else:
      avatar_url = user.avatar_url
    return UserInfo(user.id, user.user_name, avatar_url)

  @route('/<int:user_id>/avatar')
  def get_avatar(self, user_id: int):
    user = User.get(id=user_id).instance
    if user.avatar:
      return send_file(
        io.BytesIO(user.avatar.data),
        mimetype=user.avatar.content_type,
        attachment_filename='avatar.png')  # TODO: Use correct filename
    abort(404)
