import os
import openai
import telebot
import json
import sqlite3

# Установите токен вашего бота в Telegram
token = 'API telegram'

# Установите ваш ключ API от OpenAI
openai.api_key = 'Введите API openai'

bot = telebot.TeleBot(token)

# Получите абсолютный путь к рабочей директории
working_directory = os.path.dirname(os.path.abspath(__file__))

# Путь к JSON-файлу для хранения истории бесед
conversation_history_file = os.path.join(working_directory, 'conversation_history2.json')

# Подключение к базе данных SQLite
db_connection = sqlite3.connect('user_data.db')
db_cursor = db_connection.cursor()

# Создаем таблицу пользователей, если она не существует
db_cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    is_known INTEGER DEFAULT 0
                    )''')
db_connection.commit()

# Словарь для отслеживания контекста беседы
conversation_context = {}

def load_conversation_history():
    try:
        with open(conversation_history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_conversation_history(conversation_history):
    with open(conversation_history_file, 'w', encoding='utf-8') as f:
        json.dump(conversation_history, f, ensure_ascii=False, indent=4)
def get_history(chat_id):
    conversation_history = load_conversation_history()
    chat_id_str = str(chat_id)

    if chat_id_str not in conversation_history:
        conversation_history[chat_id_str] = []

    save_conversation_history(conversation_history)  # Сохраняем обновленный словарь
    return conversation_history[chat_id_str]

def add_message(chat_id, message):
    conversation_history = load_conversation_history()
    chat_id_str = str(chat_id)
    
    if chat_id_str not in conversation_history:
        conversation_history[chat_id_str] = []

    conversation_history[chat_id_str].append(message)
    save_conversation_history(conversation_history)

def message_to_dict(message):
    if message:
        return {
            "role": "user" if message.from_user and message.from_user.username else "system",
            "content": message.text,
        }
    else:
        return None
@bot.message_handler(commands=['start'])
def hello(message):
    chat_id = message.chat.id

    # Создаем новое подключение к базе данных SQLite внутри этой функции
    db_connection = sqlite3.connect('user_data.db')
    db_cursor = db_connection.cursor()

    # Проверяем, знаком ли пользователь (новый или уже известный)
    db_cursor.execute("SELECT is_known FROM users WHERE chat_id=?", (chat_id,))
    user_data = db_cursor.fetchone()

    if user_data is None:
        # Новый пользователь, устанавливаем флаг "is_known" в 1
        db_cursor.execute("INSERT INTO users (chat_id, is_known) VALUES (?, 1)", (chat_id,))
        db_connection.commit()

        # Отправляем приветственное сообщение и предоставляем доступ к обученному ИИ
        bot.send_message(chat_id, f'Салам! Добро пожаловать! Теперь вы можете начать общение со мной!')
        history = get_history(chat_id)
    else:
        # Пользователь уже известный, продолжаем общение
        bot.send_message(chat_id, f'Салам! Как я могу вам помочь?')
        history = get_history(chat_id)

    # Закрываем подключение к базе данных после использования
    db_connection.close()
@bot.message_handler(content_types=['text'])
def main(message):
    chat_id = message.chat.id
    
    # Отправляем сообщение, что бот "печатает"
    bot.send_chat_action(chat_id, 'typing')

    # Получаем имя пользователя из контекста
    user_name = conversation_context.get(chat_id, {}).get("user_name", "")

    # Получаем историю сообщений для данного чата
    history = get_history(chat_id)

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
        max_tokens=512,
        messages=[
            {"role": "system", "content": "Я юрист Кыргысзкой республики помогу написать петицию"},
            {"role": "user", "content": message.text},
            {"role": "assistant", "content": context.get('assistant_response', '')}
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