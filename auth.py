from google_auth_oauthlib.flow import InstalledAppFlow
import pickle
import os

# Укажите нужные области доступа (например, Google Sheets и Google Drive)
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']

# Удалите старый файл token.pickle, если он существует
if os.path.exists('token.pickle'):
    os.remove('token.pickle')

# Создаем поток для аутентификации
flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)

# Получаем URL авторизации с параметром access_type='offline' для получения refresh_token
creds = flow.run_local_server(port=5000, access_type='offline', prompt='consent')

# Сохраните токены для последующего использования на сервере
with open('token.pickle', 'wb') as token:
    pickle.dump(creds, token)

# Проверим наличие refresh_token
if creds.refresh_token:
    print("refresh_token получен:", creds.refresh_token)
else:
    print("refresh_token не был получен.")