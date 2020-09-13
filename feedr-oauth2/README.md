# feedr-oauth2

This small library implements the OAuth2 login flow for `code` response types and
`authorization_code` grant types.

## Quickstart

```py
from feedr_oauth2 import OAuth2Client

client = OAuth2Client(
  authorize_url='https://.../authorize',
  exchange_url='https://.../access_token',
  client_id='...',
  client_secret='...',
)

# Defaults to response_type=code and grant_type=authorization_code.
session = client.login_session()

# This stands for any intermediary logic needed to redirect the user to the login URL
# and retrieving the "code" and "state" from page they got redirected to after that.
response = redirect_user_to_page(session.login_url)

auth_data = session.get_token(response.get('code'))
print(auth_data['access_token'])
```

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
