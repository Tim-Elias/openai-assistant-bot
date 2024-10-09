from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime
import os
from dotenv import load_dotenv
import io
from google_drive.auth import creds


load_dotenv()
# ID таблицы и диапазон данных
spread_sheet_id = os.getenv('SPREADSHEET_ID')
RANGE_NAME = 'Sheet1!A2:H100'
folder_id=os.getenv('FOLDER_ID')

# Путь к вашему файлу с учетными данными
#CREDS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

# Подключение к сервисам Google
def get_drive_service():
    drive_service = build('drive', 'v3', credentials=creds)
    return drive_service

# Подключение к сервисам Google
def get_sheets_service():
    sheets_service = build('sheets', 'v4', credentials=creds)
    return sheets_service


#добавление данных из функции в гугл таблицы
def put_data_into_sheets(sheets_service, user_id, arguments):
    from utils import get_name
    # Создание клиента для доступа к Google Sheets API
    username=get_name(user_id)
    # Чтение данных
    date = str(datetime.now())
    #sheet = service.spreadsheets()
    car_model=arguments.get('car_model')
    car_number=arguments.get('car_number')
    damage=arguments.get('damage')
    text=arguments.get('text')
    links = ', '.join(arguments.get('photo_urls', []))
    # Новые данные, которые вы хотите добавить (список списков)
    new_values = [
        [username, date, car_model, car_number, damage, text, links]
    ]
    # Подготовка тела запроса
    body = {
        'values': new_values
    }
    result = sheets_service.spreadsheets().values().append(
        spreadsheetId=spread_sheet_id,
        range='Sheet1!A:Z',
        valueInputOption="RAW", 
        insertDataOption="INSERT_ROWS",  
        body=body
    ).execute()


    # Загрузка изображения в гугл диск, возвращает ссылку
def upload_to_drive(drive_service, file_name, file_data, mime_type):
    # Загрузка файла на Google Диск
    file_metadata = {
        'name': file_name,
        'parents': [folder_id],  # Здесь указываем ID папки
        'mimeType': mime_type
    }
    media = MediaIoBaseUpload(io.BytesIO(file_data), mimetype=mime_type)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    # Получение ссылки на файл
    file_id = file.get('id')
    drive_service.permissions().create(fileId=file_id, body={'role': 'reader', 'type': 'anyone'}).execute()
    link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

    return link
