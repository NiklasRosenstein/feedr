
import io

import requests
from flask import abort, send_file

from ._base import Component, route
from ..model.user import User


class UserComponent:

  @route('/<int:user_id>/avatar')
  def get_avatar(self, user_id: int):
    user = User.get(on={'id': user_id})
    if user.avatar_url:
      # TODO: This may be against TOS of the respective provider. Need to send the
      #   avatar URL instead of proxying the content.
      resp = requests.get(user.avatar_url)
      return (resp.content, resp.status_code, resp.headers.items())
    elif user.avatar:
      return send_file(io.BytesIO(user.avatar.data), mimetype=user.avatar.content_type, attachment_filename='avatar.png')
    else:
      abort(404)
