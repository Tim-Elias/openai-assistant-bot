import openai
import telebot
import io
from io import BytesIO
import os
from dotenv import load_dotenv
import json
from googleapiclient.discovery import build
from telebot.types import BotCommand
from googleapiclient.http import MediaIoBaseUpload
import pickle
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import time
import requests
from db_manager import DatabaseManager
from datetime import datetime
import threading
import mimetypes

db = DatabaseManager()

# Создаем таблицы
db.create_tables()

load_dotenv()

#класс BytesIO с именем
class NamedBytesIO(BytesIO):
    def __init__(self, initial_bytes, name):
        super().__init__(initial_bytes)
        self.name = name

#транскрибация аудио
def transcribe_audio(audio, file_format):
    # Create a BytesIO object with a name attribute
    audio_file = NamedBytesIO(audio, f"audio.{file_format}")
    # Ensure the BytesIO buffer is at the start
    audio_file.seek(0)
    try:
        #print('Дошло сюда')
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,  # Pass the file-like object (BytesIO)
            language="ru"  # Specify the language if needed
        )
        # Получаем текст из ответа
        transcribed_text = response.text
        #print(transcribed_text)
        return transcribed_text
    finally:
        # Закрываем файл BytesIO
        audio_file.close()

# Получение типа изображения
def get_mime_type(file_extension):
    mime_type, _ = mimetypes.guess_type(f"file.{file_extension}")
    if mime_type is None:
        # Значение по умолчанию, если MIME-тип не определен
        mime_type = 'application/octet-stream'
    return mime_type

# Загрузка изображения в гугл диск и в ассистента
def upload_image(file_info, thread_id):
    file_path = file_info.file_path
    file_extension = file_path.split('.')[-1]
    downloaded_file = bot.download_file(file_path)
    file_name = f"/image/{thread_id}.{file_extension}"
    mime_type = get_mime_type(file_extension)
    link = upload_to_drive(file_name, downloaded_file, mime_type)
    client.beta.threads.messages.create(thread_id=thread_id,
                                    role="user",
                                    content=link)
    
# Загрузка видео в гугл диск и в ассистента
def upload_video(file_info, thread_id):
    file_path = file_info.file_path
    file_extension = file_path.split('.')[-1]
    downloaded_file = bot.download_file(file_path)
    file_name = f"/video/{thread_id}.{file_extension}"
    mime_type = get_mime_type(file_extension)
    link = upload_to_drive(file_name, downloaded_file, mime_type)
    client.beta.threads.messages.create(thread_id=thread_id,
                                    role="user",
                                    content=link)
    
#запускаем новый ран с user_input
def create_run(message, user_input, thread_id, user_id):
    # Добавление сообщения пользователя в поток
    client.beta.threads.messages.create(thread_id=thread_id,
                                      role="user",
                                      content=user_input)
    is_put=False
    # Запуск помощника
    run = client.beta.threads.runs.create(thread_id=thread_id,
                                        assistant_id=assistant_id,
                                        max_prompt_tokens = 5000,
                                        max_completion_tokens = 10000)
    # Проверка необходимости действия в ходе выполнения
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id,
                                                   run_id=run.id)
    
    # Вывод статуса выполнения: {run_status.status}
        if run_status.status == 'completed':
            run_data=run_status.json()
            run_data=json.loads(run_data)
            prompt_tokens=run_data.get("usage", {}).get("prompt_tokens")
            completion_tokens=run_data.get("usage", {}).get("completion_tokens")
            total_tokens=run_data.get("usage", {}).get("total_tokens")
            model=run_data.get("model")
            db.add_tokens(user_id, thread_id, prompt_tokens, completion_tokens, total_tokens,model)
            # Получение и возврат последнего сообщения от помощника
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            if messages.data:
                #print(messages.data[0].content[0])
                response = messages.data[0].content[0].text.value  # Здесь response является строкой
                #print(response)
            else:
                response = "Ошибка получения ответа от помощника."
            break
        elif run_status.status=='incomplete':
            #print(run_status.json())
            response=f'Ошибка получения ответа от помощника. {run_status.status}'
        elif run_status.status == 'requires_action':
        # Обработка вызова функции
            for tool_call in run_status.required_action.submit_tool_outputs.tool_calls:
                if tool_call.function.name == "get_car_data":
                    # Создание лидов
                    arguments = json.loads(tool_call.function.arguments)
                    output = 'true'
                    client.beta.threads.runs.submit_tool_outputs(thread_id=thread_id,
                                                                run_id=run.id,
                                                                tool_outputs=[{
                                                                    "tool_call_id":
                                                                    tool_call.id,
                                                                    "output":
                                                                    json.dumps(output)
                                                                }])
                    #print(arguments, "Получено от ассистента")
                    put_data_into_sheets(message, user_id, arguments)
                    #print("Загружено")
                    is_put=True

        else:
            print(run_status.status)
        time.sleep(1)  # Ожидание одной секунды перед следующей проверкой

    # Получение и возврат последнего сообщения от помощника
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    if messages.data:
        #print(messages.data[0].content[0])
        response = messages.data[0].content[0].text.value  # Здесь response является строкой
        #print(response)
    else:
        response = "Ошибка получения ответа от помощника."
    print(response)
    return response, is_put

#получаем данные для аутентификации в гугле
def get_credentials():
    creds = None
    # Попытка загрузки токенов из файла, если он существует
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # Проверка, если токенов нет или они недействительны
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Если токен истек, используем refresh_token для его обновления
            creds.refresh(Request())
            # Сохраняем обновленные токены
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        else:
            raise Exception("Нет действительных токенов или refresh_token")

    return creds

#добавление данных из функции в гугл таблицы
def put_data_into_sheets(message, user_id, arguments):
    creds = get_credentials()
    # Создание клиента для доступа к Google Sheets API
    service = build('sheets', 'v4', credentials=creds)
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
    result = service.spreadsheets().values().append(
        spreadsheetId=spread_sheet_id,
        range='Sheet1!A:Z',
        valueInputOption="RAW", 
        insertDataOption="INSERT_ROWS",  
        body=body
    ).execute()

# Загрузка изображения в гугл диск, возвращает ссылку
def upload_to_drive(file_name, file_data, mime_type):
    creds = get_credentials()
    # Подключение к Google Drive API
    service = build('drive', 'v3', credentials=creds)
    
    # Загрузка файла на Google Диск
    file_metadata = {
        'name': file_name,
        'parents': [folder_id],  # Здесь указываем ID папки
        'mimeType': mime_type
    }
    media = MediaIoBaseUpload(io.BytesIO(file_data), mimetype=mime_type)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    # Получение ссылки на файл
    file_id = file.get('id')
    service.permissions().create(fileId=file_id, body={'role': 'reader', 'type': 'anyone'}).execute()
    link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

    return link

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
    

# Данные
openai.api_key=os.getenv('OPENAI_API_KEY')
openai_api_key=os.getenv('OPENAI_API_KEY')
tg_api_token=os.getenv('TG_API_TOKEN')
bot = telebot.TeleBot(tg_api_token)
assistant_id=os.getenv('ASSISTANTS_ID')
client = openai.OpenAI()
get_name_url=os.getenv('GET_NAME_URL')
headers={'Content-Type': 'application/json'}


# Сохранение состояния для пользователей (хранение сессий)
user_threads = {}

# Таймер для каждого пользователя
user_timers = {}


# Время ожидания для завершения приема изображений (в секундах)
WAIT_TIME = 5

# Определите область доступа
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']

# Путь к вашему файлу с учетными данными
CREDS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

# ID таблицы и диапазон данных
spread_sheet_id = os.getenv('SPREADSHEET_ID')
RANGE_NAME = 'Sheet1!A2:H100'
folder_id=os.getenv('FOLDER_ID')

# Сообщить ассисенту, что все ссылки пришли
def ask_if_more_pictures(message, thread_id, user_id):
    text='Пришли ссылки. Уточни, все ли фото прислали.'
    response, is_put=create_run(message, text, thread_id, user_id)
    if is_put:
        thread = openai.beta.threads.create()
        user_threads[user_id] = thread.id
    bot.send_message(user_id, response)

# Запуск таймера для бота
def start_timer(message, thread_id, user_id):
    """Запускает таймер для пользователя."""
    if user_id in user_timers:
        user_timers[user_id].cancel()
    # Таймер ждет указанное время, а затем запускает обработку изображений
    user_timers[user_id] = threading.Timer(WAIT_TIME, ask_if_more_pictures, args=[message, thread_id, user_id])
    user_timers[user_id].start()

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    thread = openai.beta.threads.create()
    user_threads[user_id] = thread.id
    user_id=str(user_id)
    thread_id=str(thread.id)
    username=get_name(user_id)
    exists_query=db.exists(user_id, thread_id)
    if exists_query:
        db.update_user(user_id, thread_id)
    else:
        db.add_user(user_id, thread_id)
    if username:
        content=f"Пользователя зовут {username}"
        client.beta.threads.messages.create(thread_id=thread_id,
                                      role="user",
                                      content=content)
        bot.reply_to(message, f"Здравствуйте, {username}. Расскажите о вашей проблеме.")
    else:
        bot.reply_to(message, f"Здравствуйте. Расскажите о вашей проблеме.")

# Обработка текстовых сообщений
@bot.message_handler(content_types=['text'])
def handle_question(message):
    user_id = message.chat.id
    if user_id not in user_threads:
        thread = openai.beta.threads.create()
        user_threads[user_id] = thread.id
    user_input=message.text
    thread_id = user_threads[user_id]
    print(user_input)
    response, is_put=create_run(message, user_input, thread_id, user_id)
    if is_put:
        thread = openai.beta.threads.create()
        user_threads[user_id] = thread.id
    #response = messages.data[0].content[0].text.value
    bot.reply_to(message, response)


# Обработчик фотографий
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.chat.id
    if user_id not in user_threads:
        thread = openai.beta.threads.create()
        user_threads[user_id] = thread.id  
    #user_text=message.text
    thread_id = user_threads[user_id]
    file_info = bot.get_file(message.photo[-1].file_id)
    upload_image(file_info, thread_id)
    start_timer(message, thread_id, user_id)


    
# Обработчик документов
@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.chat.id
    if user_id not in user_threads:
        thread = openai.beta.threads.create()
        user_threads[user_id] = thread.id
    thread_id = user_threads[user_id]
    # Проверяем, является ли документ изображением
    file_name = message.document.file_name
    # Список документов в сообщении (если их несколько)
    if file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
        file_info = bot.get_file(message.document.file_id)
        upload_image(file_info, thread_id) 
    else:
        bot.reply_to(message, "Пожалуйста, отправьте изображение в формате JPG или PNG.")
    start_timer(message, thread_id, user_id)


# Обработчик видео
@bot.message_handler(content_types=['video'])
def handle_video(message):
    video = message.video
    file_info = bot.get_file(video.file_id)
    user_id = message.chat.id
    if user_id not in user_threads:
        thread = openai.beta.threads.create()
        user_threads[user_id] = thread.id
    thread_id = user_threads[user_id]
    upload_video(file_info, thread_id)
    start_timer(message, thread_id, user_id)

# Обработчик аудио
@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio(message):
    user_id = message.chat.id
    if user_id not in user_threads:
        thread = openai.beta.threads.create()
        user_threads[user_id] = thread.id
    thread_id = user_threads[user_id]
    try:
        if message.content_type == 'voice':
            # Работа с голосовыми сообщениями
            file_info = bot.get_file(message.voice.file_id)
            file_format = 'ogg'
        elif message.content_type == 'audio':
            # Работа с аудиофайлами
            file_info = bot.get_file(message.audio.file_id)
            file_format = message.audio.mime_type.split('/')[1]  # Определяем формат аудиофайла
        # Скачиваем файл в память
        file_path = file_info.file_path
        downloaded_file = bot.download_file(file_path)
        try:
            #транскрибируем аудио
            text = transcribe_audio(downloaded_file, file_format)
            print(text)
        finally:
            # Очищаем загруженный файл из памяти
            del downloaded_file
        user_input=text
        response, is_put=create_run(message, user_input, thread_id, user_id)
        if is_put:
            thread = openai.beta.threads.create()
            user_threads[user_id] = thread.id
        bot.reply_to(message, response)
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.reply_to(message, f"Произошла ошибка: {e}")


def set_bot_commands(bot):
    commands = [
        BotCommand(command="/start", description="Начать новый дилог"),
    ]
    bot.set_my_commands(commands)

# Вызов функции при запуске бота
set_bot_commands(bot)


# Запуск бота
try:
    bot.polling(none_stop=True)
except Exception as e:
    print(f"Ошибка: {e}")