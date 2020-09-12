# feedr-oauth2

This small library implements the OAuth2 login flow.

## Quickstart

```py
from feedr_oauth2 import OAuth2Client

client = OAuth2Client(
  authorize_url='https://.../authorize',
  exchange_url='https://.../access_token',
  client_id='...',
  client_secret='...',
)

session = client.login_session()

# This stands for any intermediary logic needed to redirect the user to the authorize URL
# and retrieving the "code" and "state" from page they got redirected to after that.
response = redirect_user_to_page(session.authorize_url)

session.validate(response.get('state'))

auth_data = session.exchange(response.get('code'))
print(auth_data['access_token'])
```

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
