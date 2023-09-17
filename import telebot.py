import os
import openai
import telebot
import json

# Установите токен вашего бота в Telegram
token = '6581002043:AAFpjPHYO-lU_w5LwNDq0oUVOu4Cwe_Vflo'

# Установите ваш ключ API от OpenAI
openai.api_key = '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'

bot = telebot.TeleBot(token)

# Получите абсолютный путь к рабочей директории
working_directory = os.path.dirname(os.path.abspath(__file__))

# Словарь для отслеживания контекста беседы
conversation_context = {}

def get_history(chat_id):
    chat_id_str = str(chat_id) + ".json"
    history_path = os.path.join(working_directory, chat_id_str)
    
    try:
        with open(history_path, 'r', encoding='utf-8') as f:
            history = json.load(f)
    except FileNotFoundError:
        history = []

    return history, history_path

def add_message(chat_id, message):
    history, history_path = get_history(chat_id)
    history.append(message)

    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def message_to_dict(message):
    return {
        "role": "user" if message.from_user.username else "system",
        "content": message.text,
    }

@bot.message_handler(commands=['start'])
def hello(message):
    bot.send_message(message.chat.id, f'Салам ! Сизге кандай жардам керек?')
    
@bot.message_handler(content_types=['text'])
def main(message):
    chat_id = message.chat.id
    
    # Отправляем сообщение, что бот "печатает"
    bot.send_chat_action(chat_id, 'typing')

    # Получаем имя пользователя из контекста
    user_name = conversation_context.get(chat_id, {}).get("user_name", "")

    # Получаем историю сообщений для данного чата
    history, _ = get_history(chat_id)

    # Определяем контекст беседы
    context = conversation_context.get(chat_id, {})

    # Преобразуем текущее сообщение пользователя в словарь и добавляем его в историю
    user_message_dict = message_to_dict(message)
    history.append(user_message_dict)

    # Добавляем текущее сообщение в историю
    add_message(chat_id, user_message_dict)

    # Добавляем текущий запрос и историю сообщений в контекст
    context['current_request'] = message.text
    context['message_history'] = history

    # Отправляем запрос и контекст на анализ OpenAI
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a master/master/teacher for a kyrgyz child/scholkid."},
            {"role": "user", "content": message.text},
            {"role": "assistant", "content": context.get('assistant_response', '')}  # Предыдущий ответ ассистента
        ]
    )

    # Получаем ответ от OpenAI
    assistant_response = response.choices[0].message['content']

    # Преобразуем ответ системы в словарь и добавляем его в историю
    assistant_message_dict = {"role": "assistant", "content": assistant_response}
    history.append(assistant_message_dict)

    # Добавляем ответ системы в историю
    add_message(chat_id, assistant_message_dict)

    # Сохраняем ответ ассистента в контексте
    context['assistant_response'] = assistant_response
    # Отправляем ответ ассистента в Телеграм
    bot.send_message(chat_id, assistant_response)

    # Обновляем контекст беседы
    conversation_context[chat_id] = context
bot.polling(non_stop=True)
