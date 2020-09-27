
"""
Example to authenticate via a Device Code using the Google API.

Instructions to create credentials:
https://developers.google.com/identity/protocols/oauth2/limited-input-device
"""

import argparse
from feedr.oauth2.device_code import Client

parser = argparse.ArgumentParser()
parser.add_argument('--device-code-uri', default='https://oauth2.googleapis.com/device/code')
parser.add_argument('--token-uri', default='https://oauth2.googleapis.com/token')
parser.add_argument('--scope', default='email')
parser.add_argument('--client-id', required=True)
parser.add_argument('--client-secret', required=True)
args = parser.parse_args()

client = Client(
  device_code_uri=args.device_code_uri,
  token_uri=args.token_uri,
  client_id=args.client_id,
  client_secret=args.client_secret,
  scope=args.scope,
)

request = client.get_device_code()
print(f'Visit {request.verification_url} and enter the code {request.user_code}.')
print(client.poll(request))
