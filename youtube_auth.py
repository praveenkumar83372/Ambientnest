# Save this file as: youtube_auth.py
# Run this once to authenticate. It will open a browser window for Google login,
# then save a 'token.pickle' file that main.py reuses for future uploads.
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


def get_authenticated_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('client_secrets.json'):
                raise FileNotFoundError(
                    "'client_secrets.json' not found. Download it from Google Cloud Console "
                    "(YouTube Data API v3 OAuth client credentials) and place it in this folder."
                )
            flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    print("✅ Successfully authenticated YouTube API access!")
    return creds


if __name__ == "__main__":
    get_authenticated_service()