import os, pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/yt-analytics.readonly',
]

def get_authenticated_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle','rb') as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle','wb') as f:
            pickle.dump(creds, f)
    print('YouTube + Analytics auth ready!')
    return creds

if __name__ == '__main__':
    get_authenticated_service()
