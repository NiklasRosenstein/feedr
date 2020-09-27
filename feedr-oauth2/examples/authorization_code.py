
"""
Example to authenticate as a user using the browser.
"""

import argparse
import flask
import typing as t
from databind.json import to_str
from feedr.oauth2.common import raise_for_error_code
from feedr.oauth2.authorization_code import Client

parser = argparse.ArgumentParser()
parser.add_argument('--auth-uri', required=True)
parser.add_argument('--token-uri', required=True)
parser.add_argument('--client-id', required=True)
parser.add_argument('--client-secret', required=True)
parser.add_argument('--scope')
parser.add_argument('--use-pkce', action='store_true')
parser.add_argument('--port', type=int, default=8000)
args = parser.parse_args()

client = Client(
  auth_uri=args.auth_uri,
  token_uri=args.token_uri,
  client_id=args.client_id,
  client_secret=args.client_secret,
  scope=args.scope,
  use_pkce=args.use_pkce,
)

app = flask.Flask(__name__)
states = {}
EXTERNAL_URL = f'http://localhost:{args.port}'

@app.route('/login')
def login():
  request = client.authorization_request(flask.url_for('collect'))
  states[request.state] = request.pkce
  return flask.redirect(request.auth_uri)

@app.route('/collect')
def collect():
  error = t.cast(t.Optional[str], flask.request.args.get('error'))
  if error:
    raise_for_error_code(error)
  state = t.cast(str, flask.request.args['state'])
  code = t.cast(str, flask.request.args['code'])
  pkce = states.pop(state)
  token = client.authorization_code(code, pkce)
  return to_str(token), 200, [('Content-Type', 'application/json')]

print()
print(f'Visit {EXTERNAL_URL}/login to get started.')
print()

app.run(host='localhost', port=args.port, debug=True)
