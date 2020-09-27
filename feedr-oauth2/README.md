# feedr-oauth2

This is a Python library that implements the client side of following OAuth 2.0 flows:

* Authorization Code
* Client Credentials
* Device Code
* Refresh Token

The implementation follows the OAuth2 standard described in https://oauth.net/2/.

## Quickstart

### Authorization Code

```py
from feedr.oauth2.authorization_code import Client, PKCE

client = ac.Client(
  auth_uri='https://authorization-server.com/oauth2/authorize',
  token_uri='https://authorization-server.com/oauth2/token',
  client_id='...',
  client_secret='...',
  redirect_uri='...',
  use_pkce=True,
)

# ------------------
# /api/login
# ------------------

request = client.authorization_request(
  scope='read+write',
  redirect_uri=EXTERNAL_URL + '/api/login/collect',
)

persist_state(request.state, request.pkce)

return redirect(request.auth_uri)

# ------------------
# /api/login/collect?code=...&state=...
# ------------------

pkce: PKCE = retrieve_state(state)

response = client.authorization_code(code, pkce)

print(response)  # AccessTokenResponse(access_token='...', token_type='bearer', ...)
```

### Client Credentials

```py
from feedr.oauth2.client_credentials as Client

client = Client(
  token_uri='https://authorization-server.com/oauth2/token',
  client_id='...',
  client_secret='...',
)

token_info = client.get_token()
print(token_info)  # AccessTokenResponse(access_token='...', token_type='bearer', ...)
```

### Device Code

```py
from feedr.oauth2.device_code import Client

client = Client(
  device_code_uri='https://authorization-server.com/device/code',
  token_uri='https://authorization-server.com/oauth2/token',
  client_id='...',
  client_secret='...',
)

request = client.get_device_code()
print(f'Visit {request.verification_url} and enter the code {request.user_code}.')

token_info = client.poll(request)
print(token_info)  # AccessTokenResponse(access_token='...', token_type='bearer', ...)
```

### Refresh Token

The `authorization_code.Client` class has a `refresh_token()` method that makes refreshing the
access token easy by simply supplying the refresh token.

```py
new_token = client.refresh_token(token_info.refresh_token)
```

Alternatively, the `refresh_token.Client` can be used to create a `refresh_token` request.

```py
client = Client(
  token_uri='https://authorization-server.com/oauth2/token',
  refresh_token='...',
  client_id='...',
  client_secret='...',
)

token_info = client.get_token()
print(token_info)  # AccessTokenResponse(access_token='...', token_type='bearer', ...)
```

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
