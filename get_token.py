import os
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ["PISTE_CLIENT_ID"]
CLIENT_SECRET = os.environ["PISTE_CLIENT_SECRET"]

# récupérer token
url = "https://oauth.piste.gouv.fr/api/oauth/token"

data = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": "openid"
}

response = requests.post(url, data=data)
token = response.json()["access_token"]

print("TOKEN:", token)