
import io
from typing import Optional

import requests
from databind.core import datamodel
from flask import abort, send_file

from ._base import Component, route, url_for, json_response
from ..model.user import User


@datamodel
class UserInfo:
  id: int
  user_name: str
  avatar_url: Optional[str]


class UserComponent(Component):

  @route('/<int:user_id>')
  @json_response
  def get_user(self, user_id: int) -> UserInfo:
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
