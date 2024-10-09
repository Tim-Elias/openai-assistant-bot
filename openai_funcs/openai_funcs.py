import openai
from io import BytesIO
import json
import os
from dotenv import load_dotenv
import time
from google_drive import put_data_into_sheets, get_sheets_service

load_dotenv()


# Данные
openai.api_key=os.getenv('OPENAI_API_KEY')
openai_api_key=os.getenv('OPENAI_API_KEY')
client = openai.OpenAI()
assistant_id=os.getenv('ASSISTANTS_ID')
sheets_service = get_sheets_service()


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


    #запускаем новый ран с user_input
def create_run(db, user_input, thread_id, user_id):
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
                    put_data_into_sheets(sheets_service, user_id, arguments)
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


def create_thread():
    thread = openai.beta.threads.create()
    return thread

def create_message(thread_id, link):
    client.beta.threads.messages.create(thread_id=thread_id,
                                    role="user",
                                    content=link)
