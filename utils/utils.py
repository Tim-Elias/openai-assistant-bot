import os
from dotenv import load_dotenv
import requests
import json
import mimetypes
import logging
from google_drive import get_drive_service
from openai_funcs import create_message

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

get_name_url = os.getenv('GET_NAME_URL')
headers = {'Content-Type': 'application/json'}

# Получаем сервис Google Drive
try:
    drive_service = get_drive_service()
    logging.info("Сервис Google Drive успешно инициализирован.")
except Exception as e:
    logging.error(f"Ошибка инициализации сервиса Google Drive: {e}")
    drive_service = None


# Получение типа изображения
def get_mime_type(file_extension):
    try:
        mime_type, _ = mimetypes.guess_type(f"file.{file_extension}")
        if mime_type is None:
            # Значение по умолчанию, если MIME-тип не определен
            mime_type = 'application/octet-stream'
        logging.info(f"Определен MIME-тип для {file_extension}: {mime_type}")
        return mime_type
    except Exception as e:
        logging.error(f"Ошибка при определении MIME-типа для {file_extension}: {e}")
        return 'application/octet-stream'


# Загрузка изображения в Google Диск и ассистента
def upload_image(bot, file_info, thread_id):
    from google_drive import upload_to_drive
    try:
        file_path = file_info.file_path
        file_extension = file_path.split('.')[-1]
        downloaded_file = bot.download_file(file_path)
        file_name = f"/image/{thread_id}.{file_extension}"
        mime_type = get_mime_type(file_extension)

        link = upload_to_drive(drive_service, file_name, downloaded_file, mime_type)
        create_message(thread_id, link)
        logging.info(f"Изображение загружено и ссылка отправлена в ассистента: {link}")
    except Exception as e:
        logging.error(f"Ошибка загрузки изображения: {e}")


# Загрузка видео в Google Диск и ассистента
def upload_video(bot, file_info, thread_id):
    from google_drive import upload_to_drive
    try:
        file_path = file_info.file_path
        file_extension = file_path.split('.')[-1]
        downloaded_file = bot.download_file(file_path)
        file_name = f"/video/{thread_id}.{file_extension}"
        mime_type = get_mime_type(file_extension)

        link = upload_to_drive(drive_service, file_name, downloaded_file, mime_type)
        create_message(thread_id, link)
        logging.info(f"Видео загружено и ссылка отправлена в ассистента: {link}")
    except Exception as e:
        logging.error(f"Ошибка загрузки видео: {e}")


# Получение имени пользователя из внешней системы (например, 1С)
def get_name(user_id):
    data = {"id": user_id}
    try:
        logging.info(f"Отправка запроса на получение имени пользователя для ID: {user_id}")
        response = requests.post(get_name_url, data=json.dumps(data), headers=headers)
        
        if response.status_code == 200:
            try:
                data = response.json()
                name = data['data']['name']
                logging.info(f"Имя пользователя для ID {user_id}: {name}")
                return name
            except ValueError as e:
                logging.error(f"Ошибка разбора JSON-ответа: {e}")
                return None
        else:
            logging.error(f"Запрос на получение имени пользователя не удался. Код ответа: {response.status_code}")
            return None
    except requests.RequestException as e:
        logging.error(f"Ошибка запроса к внешней системе: {e}")
        return None
