import os
from dotenv import load_dotenv
import requests
import json
import mimetypes
from google_drive import get_drive_service
from openai_funcs import create_message
load_dotenv()

get_name_url=os.getenv('GET_NAME_URL')
headers={'Content-Type': 'application/json'}
drive_service = get_drive_service()


# Получение типа изображения
def get_mime_type(file_extension):
    mime_type, _ = mimetypes.guess_type(f"file.{file_extension}")
    if mime_type is None:
        # Значение по умолчанию, если MIME-тип не определен
        mime_type = 'application/octet-stream'
    return mime_type

# Загрузка изображения в гугл диск и в ассистента
def upload_image(bot, file_info, thread_id):
    from google_drive import upload_to_drive
    file_path = file_info.file_path
    file_extension = file_path.split('.')[-1]
    downloaded_file = bot.download_file(file_path)
    file_name = f"/image/{thread_id}.{file_extension}"
    mime_type = get_mime_type(file_extension)
    link = upload_to_drive(drive_service, file_name, downloaded_file, mime_type)
    create_message(thread_id, link)
    
# Загрузка видео в гугл диск и в ассистента
def upload_video(bot, file_info, thread_id):
    from google_drive import upload_to_drive
    file_path = file_info.file_path
    file_extension = file_path.split('.')[-1]
    downloaded_file = bot.download_file(file_path)
    file_name = f"/video/{thread_id}.{file_extension}"
    mime_type = get_mime_type(file_extension)
    link = upload_to_drive(file_name, downloaded_file, mime_type)
    create_message(thread_id, link)

# Получить Имя пользователя из 1с
def get_name(user_id):
    data = {"id" : user_id}
    try:
        response = requests.post(get_name_url, data=json.dumps(data), headers=headers)
        if response.status_code == 200:
            try:
                #print(response.json())
                data = response.json()
                name = data['data']['name']
                return name
            except ValueError:
                #print("Response is not a valid JSON")
                #return {'error': 'Response is not a valid JSON'}
                return None
        else:
            print(f"Request failed with status code {response.status_code}")
            return None
    except requests.RequestException as e:
        print({"error": str(e)}, 500 )
        return None