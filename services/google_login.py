import os
import requests

class GoogleLogin:
    def verify_google_token(token):
        try:
            response = requests.get(f'https://oauth2.googleapis.com/tokeninfo?id_token={token}')
            user_info = response.json()
            if response.status_code != 200 or user_info['aud'] != os.getenv('GOOGLE_CLIENT_ID'):
                return None
            return user_info
        except Exception as e:
            print(f"Error verifying token: {e}")
            return None
