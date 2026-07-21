import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]

def main():
    if not os.path.exists("client_secrets.json"):
        print("❌ Error: 'client_secrets.json' missing in E:\\ambientnestHQ!")
        return

    # Use urn:ietf:wg:oauth:2.0:oob or standard desktop redirect for out-of-band flow
    flow = InstalledAppFlow.from_client_secrets_file(
        "client_secrets.json", 
        scopes=SCOPES,
        redirect_uri="https://localhost"
    )

    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

    print("\n" + "="*70)
    print("👉 STEP 1: Copy and paste this URL into your normal Chrome browser:")
    print("="*70)
    print(f"\n{auth_url}\n")
    print("="*70)

    print("\n👉 STEP 2: Sign in, approve permissions, and after you click allow,")
    print("the browser will redirect to a page starting with 'https://localhost/?code=...'")
    print("Copy the ENTIRE URL from your Chrome address bar (or just the code value) and paste it below:\n")

    auth_response = input("Paste the full redirected URL here: ").strip()

    # Fetch token using the pasted callback URL
    flow.fetch_token(authorization_response=auth_response)

    creds = flow.credentials

    with open("token.pickle", "wb") as token:
        pickle.dump(creds, token)

    print("\n🎉 SUCCESS! 'token.pickle' generated successfully!")

if __name__ == "__main__":
    main()