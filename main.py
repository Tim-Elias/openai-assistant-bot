import telebot
import os
from dotenv import load_dotenv
from telebot.types import BotCommand
from database.db_manager import DatabaseManager
import threading
from utils import upload_image, upload_video, get_name
from openai_funcs import create_run, create_thread, create_message, transcribe_audio

db = DatabaseManager()

# Создаем таблицы
db.create_tables()

load_dotenv()

tg_api_token=os.getenv('TG_API_TOKEN')
bot = telebot.TeleBot(tg_api_token)



# Сохранение состояния для пользователей (хранение сессий)
user_threads = {}

# Таймер для каждого пользователя
user_timers = {}


# Время ожидания для завершения приема изображений (в секундах)
WAIT_TIME = 5


# Сообщить ассисенту, что все ссылки пришли
def ask_if_more_pictures(thread_id, user_id):
    text='Пришли ссылки. Уточни, все ли фото прислали.'
    response, is_put=create_run(db, text, thread_id, user_id)
    if is_put:
        thread =create_thread()
        user_threads[user_id] = thread.id
    bot.send_message(user_id, response)

# Запуск таймера для бота
def start_timer(thread_id, user_id):
    """Запускает таймер для пользователя."""
    if user_id in user_timers:
        user_timers[user_id].cancel()
    # Таймер ждет указанное время, а затем запускает обработку изображений
    user_timers[user_id] = threading.Timer(WAIT_TIME, ask_if_more_pictures, args=[ thread_id, user_id])
    user_timers[user_id].start()

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    thread = create_thread()
    user_threads[user_id] = thread.id
    user_id = str(user_id)
    thread_id = str(thread.id)
    
    # Проверяем, существует ли пользователь по user_id
    if db.exists(user_id):
        db.update_user(user_id, thread_id)
    else:
        db.add_user(user_id, thread_id)
    
    # Получаем имя пользователя и отправляем приветственное сообщение
    username = get_name(user_id)
    if username:
        content = f"Пользователя зовут {username}"
        create_message(thread_id, content)
        bot.reply_to(message, f"Здравствуйте, {username}. Расскажите о вашей проблеме.")
    else:
        bot.reply_to(message, f"Здравствуйте. Расскажите о вашей проблеме.")

# Обработка текстовых сообщений
@bot.message_handler(content_types=['text'])
def handle_question(message):
    user_id = message.chat.id
    if user_id not in user_threads:
        thread = create_thread()
        user_threads[user_id] = thread.id
    user_input=message.text
    thread_id = user_threads[user_id]
    print(user_input)
    response, is_put=create_run(db, user_input, thread_id, user_id)
    if is_put:
        thread = create_thread()
        user_threads[user_id] = thread.id
    #response = messages.data[0].content[0].text.value
    bot.reply_to(message, response)


# Обработчик фотографий
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.chat.id
    if user_id not in user_threads:
        thread = create_thread()
        user_threads[user_id] = thread.id  
    #user_text=message.text
    thread_id = user_threads[user_id]
    file_info = bot.get_file(message.photo[-1].file_id)
    upload_image(bot, file_info, thread_id)
    start_timer(thread_id, user_id)


    
# Обработчик документов
@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.chat.id
    if user_id not in user_threads:
        thread = create_thread()
        user_threads[user_id] = thread.id
    thread_id = user_threads[user_id]
    # Проверяем, является ли документ изображением
    file_name = message.document.file_name
    # Список документов в сообщении (если их несколько)
    if file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
        file_info = bot.get_file(message.document.file_id)
        upload_image(bot, file_info, thread_id) 
    else:
        bot.reply_to(message, "Пожалуйста, отправьте изображение в формате JPG или PNG.")
    start_timer(thread_id, user_id)


# Обработчик видео
@bot.message_handler(content_types=['video'])
def handle_video(message):
    video = message.video
    file_info = bot.get_file(video.file_id)
    user_id = message.chat.id
    if user_id not in user_threads:
        thread = create_thread()
        user_threads[user_id] = thread.id
    thread_id = user_threads[user_id]
    upload_video(bot, file_info, thread_id)
    start_timer(message, thread_id, user_id)

# Обработчик аудио
@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio(message):
    user_id = message.chat.id
    if user_id not in user_threads:
        thread = create_thread()
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
        response, is_put=create_run(db, user_input, thread_id, user_id)
        if is_put:
            thread = create_thread()
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