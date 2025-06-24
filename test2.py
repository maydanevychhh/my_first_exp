import telebot
from telebot import types
import datetime
import sqlite3
import requests
import json
import  re

# Токен вашого клієнтського бота
CLIENT_BOT_TOKEN = '7562102327:AAEIZcrgK1IEuy2MXmOAz1KykVGEAfs21go'
# Токен адмін бота для відправки повідомлень
ADMIN_BOT_TOKEN = '7803618226:AAE5ZODt8sY4c2oRKxnVO2VbsOjftbuBuEo'
# ID адміністратора
ADMIN_CHAT_ID = '360396387'

bot = telebot.TeleBot(CLIENT_BOT_TOKEN)


# Ініціалізація бази даних
def init_db():
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    # Спочатку перевіряємо чи існує таблиця
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            phone TEXT,
            service TEXT,
            price INTEGER,
            date TEXT,
            time TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Перевіряємо структуру таблиці і додаємо відсутні колонки
    cursor.execute("PRAGMA table_info(bookings)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'first_name' not in columns:
        cursor.execute('ALTER TABLE bookings ADD COLUMN first_name TEXT')

    if 'username' not in columns:
        cursor.execute('ALTER TABLE bookings ADD COLUMN username TEXT')

    if 'phone' not in columns:
        cursor.execute('ALTER TABLE bookings ADD COLUMN phone TEXT')

    if 'service' not in columns:
        cursor.execute('ALTER TABLE bookings ADD COLUMN service TEXT')

    if 'price' not in columns:
        cursor.execute('ALTER TABLE bookings ADD COLUMN price INTEGER')

    if 'date' not in columns:
        cursor.execute('ALTER TABLE bookings ADD COLUMN date TEXT')

    if 'time' not in columns:
        cursor.execute('ALTER TABLE bookings ADD COLUMN time TEXT')

    if 'created_at' not in columns:
        cursor.execute('ALTER TABLE bookings ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')

    conn.commit()
    conn.close()


# Послуги з цінами
SERVICES = {
    "Корекція + фарбування": 400,
    "Корекція + прорідження": 300,
    "Ламінування + корекція + фарбування": 600,
    "Ламінування + корекція": 500,
    "Ваксинг зони на обличчі": 100
}

# Часи для запису
TIME_SLOTS = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"]

# Зберігання тимчасових даних користувачів
user_data = {}


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📅 Записатися"))
    markup.add(types.KeyboardButton("ℹ️ Інформація"))

    bot.send_message(
        message.chat.id,
        "Вітаю! 🌸\n\nЯ допоможу вам записатися на послуги з догляду за бровами.\n\nОберіть дію:",
        reply_markup=markup
    )


@bot.message_handler(func=lambda message: message.text == "📅 Записатися")
def book_appointment(message):
    markup = types.InlineKeyboardMarkup()
    for service, price in SERVICES.items():
        markup.add(types.InlineKeyboardButton(
            f"{service} - {price} грн",
            callback_data=f"service_{list(SERVICES.keys()).index(service)}"
        ))

    bot.send_message(
        message.chat.id,
        "Оберіть послугу:",
        reply_markup=markup
    )


@bot.message_handler(func=lambda message: message.text == "ℹ️ Інформація")
def info(message):
    info_text = "📋 Наші послуги:\n\n"
    for service, price in SERVICES.items():
        info_text += f"• {service} - {price} грн\n"

    info_text += "\n⏰ Час роботи: 10:00 - 18:00\n📍 Адреса: [Київська 14Б]"

    bot.send_message(message.chat.id, info_text)


@bot.callback_query_handler(func=lambda call: call.data.startswith('service_'))
def handle_service_selection(call):
    service_index = int(call.data.split('_')[1])
    service_name = list(SERVICES.keys())[service_index]

    user_data[call.from_user.id] = {
        'service': service_name,
        'price': SERVICES[service_name]
    }

    # Генерація дат на наступні 14 днів
    markup = types.InlineKeyboardMarkup()
    today = datetime.date.today()

    for i in range(1, 15):  # Починаємо з завтрашнього дня
        date = today + datetime.timedelta(days=i)
        if date.weekday() < 6:  # Пн-Сб (0-5)
            date_str = date.strftime("%d.%m.%Y")
            weekday = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"][date.weekday()]
            markup.add(types.InlineKeyboardButton(
                f"{weekday} {date_str}",
                callback_data=f"date_{date.strftime('%Y-%m-%d')}"
            ))

    bot.edit_message_text(
        f"Ви обрали: {service_name} - {SERVICES[service_name]} грн\n\nОберіть дату:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('date_'))
def handle_date_selection(call):
    selected_date = call.data.split('_')[1]
    user_data[call.from_user.id]['date'] = selected_date

    # Перевіряємо доступні часи для вибраної дати
    available_times = get_available_times(selected_date)

    markup = types.InlineKeyboardMarkup()
    for time_slot in available_times:
        markup.add(types.InlineKeyboardButton(
            time_slot,
            callback_data=f"time_{time_slot}"
        ))

    if not available_times:
        markup.add(types.InlineKeyboardButton(
            "← Назад до вибору дати",
            callback_data="back_to_dates"
        ))
        text = "На жаль, на цю дату немає вільних слотів. Оберіть іншу дату."
    else:
        text = f"Дата: {datetime.datetime.strptime(selected_date, '%Y-%m-%d').strftime('%d.%m.%Y')}\n\nОберіть час:"

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('time_'))
def handle_time_selection(call):
    selected_time = call.data.split('_')[1]
    user_data[call.from_user.id]['time'] = selected_time

    bot.edit_message_text(
        "Будь ласка, надішліть ваш номер телефону для зв'язку:",
        call.message.chat.id,
        call.message.message_id
    )

    bot.register_next_step_handler(call.message, get_phone_number)


def get_phone_number(message):
    if message.content_type != 'text':
        bot.send_message(message.chat.id, "Будь ласка, введіть номер телефону текстом:")
        bot.register_next_step_handler(message, get_phone_number)
        return

    phone = message.text.strip()
    user_id = message.from_user.id

    # Перевірка: чи це номер телефону (наприклад, +380 або 0XXX...)
    phone_pattern = re.compile(r'^(\+380\d{9}|0\d{9})$')
    if not phone_pattern.match(phone):
        bot.send_message(message.chat.id, "Будь ласка, введіть коректний номер телефону у форматі +380XXXXXXXXX або 0XXXXXXXXX:")
        bot.register_next_step_handler(message, get_phone_number)
        return

    if user_id not in user_data:
        bot.send_message(message.chat.id, "Щось пішло не так. Спробуйте почати спочатку /start")
        return
    # Зберігаємо номер телефону
    user_data[user_id]['phone'] = phone
    # Показуємо підтвердження
    data = user_data[user_id]
    date_formatted = datetime.datetime.strptime(data['date'], '%Y-%m-%d').strftime('%d.%m.%Y')

    confirmation_text = f"""
📋 Підтвердження запису:

👤 Ім'я: {message.from_user.first_name or 'Не вказано'}
📱 Телефон: {phone}
💅 Послуга: {data['service']}
💰 Ціна: {data['price']} грн
📅 Дата: {date_formatted}
🕐 Час: {data['time']}

Підтвердити запис?
    """

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Підтвердити", callback_data="confirm_booking"),
        types.InlineKeyboardButton("❌ Скасувати", callback_data="cancel_booking")
    )

    bot.send_message(message.chat.id, confirmation_text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'confirm_booking')
def confirm_booking(call):
    user_id = call.from_user.id

    if user_id not in user_data:
        bot.answer_callback_query(call.id, "Дані не знайдено")
        return

    data = user_data[user_id]

    # Зберігаємо в базу даних
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO bookings (user_id, username, first_name, phone, service, price, date, time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        call.from_user.username or '',
        call.from_user.first_name or '',
        data['phone'],
        data['service'],
        data['price'],
        data['date'],
        data['time']
    ))
    conn.commit()
    booking_id = cursor.lastrowid
    conn.close()

    # Відправляємо повідомлення адміністратору
    send_admin_notification(data, call.from_user, booking_id)

    # Підтверджуємо клієнту
    date_formatted = datetime.datetime.strptime(data['date'], '%Y-%m-%d').strftime('%d.%m.%Y')

    bot.edit_message_text(
        f"✅ Ваш запис підтверджено!\n\n"
        f"📋 Номер запису: #{booking_id}\n"
        f"📅 {date_formatted} о {data['time']}\n"
        f"💅 {data['service']}\n"
        f"💰 {data['price']} грн\n\n"
        f"Очікуємо на вас! 🌸\n"
        f"При необхідності скасування зверніться до адміністратора.",
        call.message.chat.id,
        call.message.message_id
    )

    # Очищуємо тимчасові дані
    del user_data[user_id]


@bot.callback_query_handler(func=lambda call: call.data == 'cancel_booking')
def cancel_booking(call):
    user_id = call.from_user.id
    if user_id in user_data:
        del user_data[user_id]

    bot.edit_message_text(
        "❌ Запис скасовано.\n\nДля нового запису натисніть 📅 Записатися",
        call.message.chat.id,
        call.message.message_id
    )


def get_available_times(date):
    """Отримує доступні часи для конкретної дати"""
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute('SELECT time FROM bookings WHERE date = ?', (date,))
    booked_times = [row[0] for row in cursor.fetchall()]
    conn.close()

    available = [time for time in TIME_SLOTS if time not in booked_times]
    return available


def send_admin_notification(data, user, booking_id):
    """Відправляє повідомлення адміністратору про новий запис"""
    date_formatted = datetime.datetime.strptime(data['date'], '%Y-%m-%d').strftime('%d.%m.%Y')

    admin_text = f"""
🆕 НОВИЙ ЗАПИС #{booking_id}

👤 Клієнт: {user.first_name or 'Не вказано'}
📱 Username: @{user.username or 'Не вказано'}
📞 Телефон: {data['phone']}
💅 Послуга: {data['service']}
💰 Ціна: {data['price']} грн
📅 Дата: {date_formatted}
🕐 Час: {data['time']}
📊 ID користувача: {user.id}
    """

    try:
        # Відправляємо через API адмін бота
        url = f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': ADMIN_CHAT_ID,
            'text': admin_text,
            'parse_mode': 'HTML'
        }
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Помилка відправки повідомлення адміністратору: {e}")


if __name__ == '__main__':
    init_db()
    print("Клієнтський бот запущено...")
    bot.infinity_polling()