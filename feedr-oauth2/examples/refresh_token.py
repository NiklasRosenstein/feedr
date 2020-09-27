
import argparse
from feedr.oauth2.refresh_token import Client

parser = argparse.ArgumentParser()
parser.add_argument('--token-uri', required=True)
parser.add_argument('--refresh-token', required=True)
parser.add_argument('--scope')
parser.add_argument('--client-id')
parser.add_argument('--client-secret')
args = parser.parse_args()

client = Client(
  token_uri=args.token_uri,
  refresh_token=args.refresh_token,
  scope=args.scope,
  client_id=args.client_id,
  client_secret=args.client_secret,
)

print(client.get_token())
