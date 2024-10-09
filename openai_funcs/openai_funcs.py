import openai
from io import BytesIO
import json
import os
import logging
from dotenv import load_dotenv
import time
from google_drive import put_data_into_sheets, get_sheets_service

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

# Данные
openai.api_key = os.getenv('OPENAI_API_KEY')
openai_api_key = os.getenv('OPENAI_API_KEY')
client = openai.OpenAI()
assistant_id = os.getenv('ASSISTANTS_ID')

# Получаем сервис для работы с Google Sheets
try:
    sheets_service = get_sheets_service()
    logging.info("Сервис Google Sheets успешно инициализирован.")
except Exception as e:
    logging.error(f"Ошибка инициализации сервиса Google Sheets: {e}")
    sheets_service = None

# Класс NamedBytesIO с именем
class NamedBytesIO(BytesIO):
    def __init__(self, initial_bytes, name):
        super().__init__(initial_bytes)
        self.name = name

# Транскрибация аудио
def transcribe_audio(audio, file_format):
    logging.info(f"Начало транскрибирования аудио. Формат: {file_format}")
    audio_file = NamedBytesIO(audio, f"audio.{file_format}")
    audio_file.seek(0)
    try:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,  # Передача объекта BytesIO
            language="ru"  # Указание языка
        )
        transcribed_text = response.text
        logging.info(f"Транскрибация завершена. Текст: {transcribed_text}")
        return transcribed_text
    except Exception as e:
        logging.error(f"Ошибка при транскрибации аудио: {e}")
        return None
    finally:
        audio_file.close()

# Запуск нового рана с user_input
def create_run(db, user_input, thread_id, user_id):
    logging.info(f"Запуск нового рана для пользователя {user_id} в потоке {thread_id}")
    try:
        # Добавление сообщения пользователя в поток
        client.beta.threads.messages.create(thread_id=thread_id, role="user", content=user_input)
        is_put = False
        
        # Запуск помощника
        run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id, max_prompt_tokens=5000, max_completion_tokens=10000)

        while True:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

            if run_status.status == 'completed':
                run_data = json.loads(run_status.json())
                prompt_tokens = run_data.get("usage", {}).get("prompt_tokens")
                completion_tokens = run_data.get("usage", {}).get("completion_tokens")
                total_tokens = run_data.get("usage", {}).get("total_tokens")
                model = run_data.get("model")
                
                # Добавляем данные токенов в базу
                db.add_tokens(user_id, thread_id, prompt_tokens, completion_tokens, total_tokens, model)

                # Получение последнего сообщения от помощника
                messages = client.beta.threads.messages.list(thread_id=thread_id)
                if messages.data:
                    response = messages.data[0].content[0].text.value
                else:
                    response = "Ошибка получения ответа от помощника."
                break

            elif run_status.status == 'requires_action':
                for tool_call in run_status.required_action.submit_tool_outputs.tool_calls:
                    if tool_call.function.name == "get_car_data":
                        arguments = json.loads(tool_call.function.arguments)
                        output = 'true'
                        client.beta.threads.runs.submit_tool_outputs(thread_id=thread_id, run_id=run.id, tool_outputs=[{
                            "tool_call_id": tool_call.id,
                            "output": json.dumps(output)
                        }])
                        put_data_into_sheets(sheets_service, user_id, arguments)
                        is_put = True

            elif run_status.status == 'incomplete':
                logging.warning(f"Ошибка: статус рана {run_status.status}. Продолжаем ожидание.")
            else:
                logging.error(f"Неизвестный статус рана: {run_status.status}")
            
            time.sleep(1)  # Ожидание перед следующим запросом статуса

        # Повторное получение и возврат последнего сообщения
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        if messages.data:
            response = messages.data[0].content[0].text.value
        else:
            response = "Ошибка получения ответа от помощника."

        logging.info(f"Ответ от ассистента получен: {response}")
        return response, is_put

    except Exception as e:
        logging.error(f"Ошибка при запуске рана: {e}")
        return "Произошла ошибка при обработке вашего запроса.", False

def create_thread():
    try:
        thread = openai.beta.threads.create()
        logging.info(f"Создан новый поток: {thread.id}")
        return thread
    except Exception as e:
        logging.error(f"Ошибка при создании потока: {e}")
        return None

def create_message(thread_id, link):
    try:
        client.beta.threads.messages.create(thread_id=thread_id, role="user", content=link)
        logging.info(f"Сообщение создано в потоке {thread_id}: {link}")
    except Exception as e:
        logging.error(f"Ошибка при создании сообщения в потоке {thread_id}: {e}")
