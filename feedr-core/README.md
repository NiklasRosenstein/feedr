# feedr-core

Contains the core functionality that the backend is built upon (basically any re-usable code
that is not strictly tied to backend logic).

## Web package

The `feedr.core.web` package provides an extension layer on top of the Flask web framework to
create pluggable views.

### Quickstart

```py
import flask
from feedr.core.web import Route, View

@Route('/profile')
class ProfileView(View):

  @Route('/me')
  def me(self):
    return flask.render_template('profile/page.html', user=get_current_user())

  @Route('/<user_id>')
  def for_user(self, user_id):
    return flask.render_template('profile/me.html'. user=get_user(user_id))

app = flask.Flask(__name__)
ProfileView().bind(app)
```

### Rest API Example

```py
import flask
from dataclasses import dataclass
from feedr.core.web import Body, Parameters, Query, register_serde, Route, View

@dataclass
class User:
  name: str
  email: str

@Route('/user', content_type='application/json')
class UserApi(View):

  @Route('/me')
  def me(self) -> User:
    return User('john', 'john@johnwick.com')

  @Route('/create', methods=['POST'])
  @Parameters(details=Body(), update_if_exists=Query('updateIfExists'))
  def create_user(self, details: User, update_if_exists: bool) -> None:
    save_user(details, update_if_exists)

app = flask.Flask(__name__)
UserApi().bind(app)
```

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
