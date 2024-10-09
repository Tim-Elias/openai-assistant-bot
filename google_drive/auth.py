from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from google.oauth2.service_account import Credentials

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']
TOKEN_FILE = 'token.json'
# Авторизация
creds = Credentials.from_service_account_file(TOKEN_FILE, scopes=SCOPES)

