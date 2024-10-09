import telebot
import os
import logging
from dotenv import load_dotenv
from telebot.types import BotCommand
from database.db_manager import DatabaseManager
import threading
from utils import upload_image, upload_video, get_name
from openai_funcs import create_run, create_thread, create_message, transcribe_audio

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

db = DatabaseManager()

try:
    # Создаем таблицы
    db.create_tables()
    logging.info("Таблицы успешно созданы.")
except Exception as e:
    logging.error(f"Ошибка создания таблиц: {e}")

load_dotenv()

tg_api_token = os.getenv('TG_API_TOKEN')
bot = telebot.TeleBot(tg_api_token)

# Сохранение состояния для пользователей (хранение сессий)
user_threads = {}
user_timers = {}

# Время ожидания для завершения приема изображений (в секундах)
WAIT_TIME = 5

def ask_if_more_pictures(thread_id, user_id):
    try:
        text = 'Пришли ссылки. Уточни, все ли фото прислали.'
        response, is_put = create_run(db, text, thread_id, user_id)
        if is_put:
            thread = create_thread()
            user_threads[user_id] = thread.id
        bot.send_message(user_id, response)
        logging.info(f"Сообщение пользователю {user_id} отправлено: {response}")
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")

def start_timer(thread_id, user_id):
    """Запускает таймер для пользователя."""
    try:
        if user_id in user_timers:
            user_timers[user_id].cancel()
        user_timers[user_id] = threading.Timer(WAIT_TIME, ask_if_more_pictures, args=[thread_id, user_id])
        user_timers[user_id].start()
        logging.info(f"Таймер для пользователя {user_id} запущен.")
    except Exception as e:
        logging.error(f"Ошибка при запуске таймера для пользователя {user_id}: {e}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user_id = message.chat.id
        thread = create_thread()
        user_threads[user_id] = thread.id
        user_id = str(user_id)
        thread_id = str(thread.id)
        
        if db.exists(user_id):
            db.update_user(user_id, thread_id)
            logging.info(f"Пользователь {user_id} обновлен в базе данных.")
        else:
            db.add_user(user_id, thread_id)
            logging.info(f"Пользователь {user_id} добавлен в базу данных.")
        
        username = get_name(user_id)
        if username:
            content = f"Пользователя зовут {username}"
            create_message(thread_id, content)
            bot.reply_to(message, f"Здравствуйте, {username}. Расскажите о вашей проблеме.")
            logging.info(f"Приветственное сообщение отправлено пользователю {user_id}.")
        else:
            bot.reply_to(message, f"Здравствуйте. Расскажите о вашей проблеме.")
            logging.info(f"Приветственное сообщение без имени отправлено пользователю {user_id}.")
    except Exception as e:
        logging.error(f"Ошибка в обработчике команды /start: {e}")
        bot.reply_to(message, f"Произошла ошибка: {e}")

@bot.message_handler(content_types=['text'])
def handle_question(message):
    try:
        user_id = message.chat.id
        if user_id not in user_threads:
            thread = create_thread()
            user_threads[user_id] = thread.id
        user_input = message.text
        thread_id = user_threads[user_id]
        response, is_put = create_run(db, user_input, thread_id, user_id)
        if is_put:
            thread = create_thread()
            user_threads[user_id] = thread.id
        bot.reply_to(message, response)
        logging.info(f"Ответ пользователю {user_id}: {response}")
    except Exception as e:
        logging.error(f"Ошибка при обработке вопроса пользователя {user_id}: {e}")
        bot.reply_to(message, f"Произошла ошибка: {e}")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        user_id = message.chat.id
        if user_id not in user_threads:
            thread = create_thread()
            user_threads[user_id] = thread.id  
        thread_id = user_threads[user_id]
        file_info = bot.get_file(message.photo[-1].file_id)
        upload_image(bot, file_info, thread_id)
        start_timer(thread_id, user_id)
        logging.info(f"Фото от пользователя {user_id} обработано.")
    except Exception as e:
        logging.error(f"Ошибка при обработке фото от пользователя {user_id}: {e}")
        bot.reply_to(message, f"Произошла ошибка: {e}")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    try:
        user_id = message.chat.id
        if user_id not in user_threads:
            thread = create_thread()
            user_threads[user_id] = thread.id
        thread_id = user_threads[user_id]
        file_name = message.document.file_name
        if file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
            file_info = bot.get_file(message.document.file_id)
            upload_image(bot, file_info, thread_id)
        else:
            bot.reply_to(message, "Пожалуйста, отправьте изображение в формате JPG или PNG.")
        start_timer(thread_id, user_id)
        logging.info(f"Документ от пользователя {user_id} обработан.")
    except Exception as e:
        logging.error(f"Ошибка при обработке документа от пользователя {user_id}: {e}")
        bot.reply_to(message, f"Произошла ошибка: {e}")

@bot.message_handler(content_types=['video'])
def handle_video(message):
    try:
        user_id = message.chat.id
        if user_id not in user_threads:
            thread = create_thread()
            user_threads[user_id] = thread.id
        thread_id = user_threads[user_id]
        file_info = bot.get_file(message.video.file_id)
        upload_video(bot, file_info, thread_id)
        start_timer(thread_id, user_id)
        logging.info(f"Видео от пользователя {user_id} обработано.")
    except Exception as e:
        logging.error(f"Ошибка при обработке видео от пользователя {user_id}: {e}")
        bot.reply_to(message, f"Произошла ошибка: {e}")

@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio(message):
    try:
        user_id = message.chat.id
        if user_id not in user_threads:
            thread = create_thread()
            user_threads[user_id] = thread.id
        thread_id = user_threads[user_id]
        
        if message.content_type == 'voice':
            file_info = bot.get_file(message.voice.file_id)
            file_format = 'ogg'
        elif message.content_type == 'audio':
            file_info = bot.get_file(message.audio.file_id)
            file_format = message.audio.mime_type.split('/')[1]
        
        file_path = file_info.file_path
        downloaded_file = bot.download_file(file_path)
        try:
            text = transcribe_audio(downloaded_file, file_format)
            logging.info(f"Транскрибированный текст: {text}")
        finally:
            del downloaded_file

        response, is_put = create_run(db, text, thread_id, user_id)
        if is_put:
            thread = create_thread()
            user_threads[user_id] = thread.id
        bot.reply_to(message, response)
    except Exception as e:
        logging.error(f"Ошибка при обработке аудио от пользователя {user_id}: {e}")
        bot.reply_to(message, f"Произошла ошибка: {e}")

def set_bot_commands(bot):
    try:
        commands = [BotCommand(command="/start", description="Начать новый дилог")]
        bot.set_my_commands(commands)
        logging.info("Команды бота успешно установлены.")
    except Exception as e:
        logging.error(f"Ошибка при установке команд бота: {e}")

# Вызов функции при запуске бота
set_bot_commands(bot)

try:
    bot.polling(none_stop=True)
except Exception as e:
    logging.error(f"Ошибка при запуске бота: {e}")
