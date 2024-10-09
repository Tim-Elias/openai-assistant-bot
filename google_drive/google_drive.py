from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.transport.requests import Request
from datetime import datetime
import os
from dotenv import load_dotenv
import io
import logging
from google_drive.auth import creds

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

# ID таблицы и диапазон данных
spread_sheet_id = os.getenv('SPREADSHEET_ID')
RANGE_NAME = 'Sheet1!A2:H100'
folder_id = os.getenv('FOLDER_ID')

TOKEN_FILE = 'token.json'

# Подключение к сервису Google Drive
def get_drive_service():
    try:
        drive_service = build('drive', 'v3', credentials=creds)
        logging.info("Успешное подключение к Google Drive.")
        return drive_service
    except Exception as e:
        logging.error(f"Ошибка при подключении к Google Drive: {e}")
        return None

# Подключение к сервису Google Sheets
def get_sheets_service():
    try:
        sheets_service = build('sheets', 'v4', credentials=creds)
        logging.info("Успешное подключение к Google Sheets.")
        return sheets_service
    except Exception as e:
        logging.error(f"Ошибка при подключении к Google Sheets: {e}")
        return None

# Добавление данных в Google Sheets
def put_data_into_sheets(sheets_service, user_id, arguments):
    from utils import get_name
    try:
        username = get_name(user_id)
        date = str(datetime.now())
        car_model = arguments.get('car_model')
        car_number = arguments.get('car_number')
        damage = arguments.get('damage')
        text = arguments.get('text')
        links = ', '.join(arguments.get('photo_urls', []))
        
        # Новые данные для добавления
        new_values = [
            [username, date, car_model, car_number, damage, text, links]
        ]
        
        # Подготовка тела запроса
        body = {'values': new_values}
        
        # Добавление данных
        result = sheets_service.spreadsheets().values().append(
            spreadsheetId=spread_sheet_id,
            range='Sheet1!A:Z',
            valueInputOption="RAW", 
            insertDataOption="INSERT_ROWS",  
            body=body
        ).execute()
        logging.info(f"Данные успешно добавлены в Google Sheets для пользователя {username}.")
    except Exception as e:
        logging.error(f"Ошибка при добавлении данных в Google Sheets: {e}")

# Загрузка файла в Google Drive и получение ссылки
def upload_to_drive(drive_service, file_name, file_data, mime_type):
    try:
        # Подготовка метаданных файла
        file_metadata = {
            'name': file_name,
            'parents': [folder_id],  # ID папки
            'mimeType': mime_type
        }
        
        media = MediaIoBaseUpload(io.BytesIO(file_data), mimetype=mime_type)
        
        # Загрузка файла
        file = drive_service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        
        # Установка прав доступа "чтение для всех"
        drive_service.permissions().create(
            fileId=file_id, 
            body={'role': 'reader', 'type': 'anyone'}
        ).execute()
        
        # Получение ссылки на файл
        link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        logging.info(f"Файл {file_name} успешно загружен в Google Drive. Ссылка: {link}")
        
        return link
    except Exception as e:
        logging.error(f"Ошибка при загрузке файла в Google Drive: {e}")
        return None
