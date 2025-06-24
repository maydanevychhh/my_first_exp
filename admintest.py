import telebot
from telebot import types
import sqlite3
import datetime
import calendar

# Токен адмін бота
ADMIN_BOT_TOKEN = '7803618226:AAE5ZODt8sY4c2oRKxnVO2VbsOjftbuBuEo'
# ID адміністратора (ваш Telegram ID)
ADMIN_CHAT_ID = '360396387'

bot = telebot.TeleBot(ADMIN_BOT_TOKEN)


# Функція для отримання інформації про структуру таблиці
def check_table_structure():
    """Перевіряє структуру таблиці bookings"""
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(bookings)")
        columns = cursor.fetchall()
        print("Структура таблиці bookings:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        return len(columns)
    except Exception as e:
        print(f"Помилка при перевірці таблиці: {e}")
        return 0
    finally:
        conn.close()


# Безпечна функція для отримання записів
def get_booking_data(booking_tuple):
    """Безпечно розпаковує дані про запис"""
    try:
        if len(booking_tuple) >= 10:
            return {
                'id': booking_tuple[0],
                'user_id': booking_tuple[1],
                'username': booking_tuple[2] or 'Не вказано',
                'first_name': booking_tuple[3] or 'Не вказано',
                'phone': booking_tuple[4] or 'Не вказано',
                'service': booking_tuple[5] or 'Не вказано',
                'price': booking_tuple[6] or 0,
                'date': booking_tuple[7] or '',
                'time': booking_tuple[8] or '',
                'created_at': booking_tuple[9] if len(booking_tuple) > 9 else ''
            }
        else:
            # Якщо менше колонок, працюємо з тим що є
            return {
                'id': booking_tuple[0] if len(booking_tuple) > 0 else 0,
                'user_id': booking_tuple[1] if len(booking_tuple) > 1 else 0,
                'username': booking_tuple[2] if len(booking_tuple) > 2 else 'Не вказано',
                'first_name': booking_tuple[3] if len(booking_tuple) > 3 else 'Не вказано',
                'phone': booking_tuple[4] if len(booking_tuple) > 4 else 'Не вказано',
                'service': booking_tuple[5] if len(booking_tuple) > 5 else 'Не вказано',
                'price': booking_tuple[6] if len(booking_tuple) > 6 else 0,
                'date': booking_tuple[7] if len(booking_tuple) > 7 else '',
                'time': booking_tuple[8] if len(booking_tuple) > 8 else '',
                'created_at': booking_tuple[9] if len(booking_tuple) > 9 else ''
            }
    except Exception as e:
        print(f"Помилка при розпакуванні даних: {e}")
        return None


# Перевірка доступу адміністратора
def is_admin(user_id):
    return str(user_id) == str(ADMIN_CHAT_ID)


@bot.message_handler(commands=['start'])
def start(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ У вас немає доступу до цього бота.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📅 Записи на сьогодні"),
        types.KeyboardButton("🗓 Записи на завтра")
    )
    markup.add(
        types.KeyboardButton("📊 Всі записи"),
        types.KeyboardButton("🔍 Пошук запису")
    )
    markup.add(
        types.KeyboardButton("📈 Статистика"),
        types.KeyboardButton("🗓 Календар записів")
    )

    bot.send_message(
        message.chat.id,
        "🔧 Адмін панель\n\nОберіть дію:",
        reply_markup=markup
    )


@bot.message_handler(func=lambda message: message.text == "📅 Записи на сьогодні")
def today_bookings(message):
    if not is_admin(message.from_user.id):
        return

    today = datetime.date.today().strftime('%Y-%m-%d')
    show_bookings_for_date(message, today, "Записи на сьогодні")


@bot.message_handler(func=lambda message: message.text == "🗓 Записи на завтра")
def tomorrow_bookings(message):
    if not is_admin(message.from_user.id):
        return

    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    show_bookings_for_date(message, tomorrow, "Записи на завтра")


@bot.message_handler(func=lambda message: message.text == "📊 Всі записи")
def all_bookings(message):
    if not is_admin(message.from_user.id):
        return

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM bookings 
        ORDER BY date ASC, time ASC
        LIMIT 50
    ''')
    bookings = cursor.fetchall()
    conn.close()

    if not bookings:
        bot.send_message(message.chat.id, "📭 Записів не знайдено")
        return

    text = "📊 Останні 50 записів:\n\n"

    for booking_tuple in bookings:
        booking = get_booking_data(booking_tuple)
        if booking is None:
            continue

        try:
            date_formatted = datetime.datetime.strptime(booking['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
        except:
            date_formatted = booking['date']

        text += f"#{booking['id']} | {date_formatted} {booking['time']}\n"
        text += f"👤 {booking['first_name']} (@{booking['username']})\n"
        text += f"📞 {booking['phone']}\n"
        text += f"💅 {booking['service']} - {booking['price']}грн\n"
        text += "─" * 30 + "\n"

    # Розбиваємо на частини якщо повідомлення занадто довге
    if len(text) > 4000:
        parts = [text[i:i + 4000] for i in range(0, len(text), 4000)]
        for part in parts:
            bot.send_message(message.chat.id, part)
    else:
        bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda message: message.text == "🔍 Пошук запису")
def search_booking(message):
    if not is_admin(message.from_user.id):
        return

    bot.send_message(message.chat.id, "Введіть номер запису або номер телефону:")
    bot.register_next_step_handler(message, handle_search)


def handle_search(message):
    search_term = message.text.strip()

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    # Пошук за ID або телефоном
    if search_term.isdigit():
        cursor.execute('SELECT * FROM bookings WHERE id = ? OR phone LIKE ?',
                       (search_term, f'%{search_term}%'))
    else:
        cursor.execute('SELECT * FROM bookings WHERE phone LIKE ? OR first_name LIKE ?',
                       (f'%{search_term}%', f'%{search_term}%'))

    bookings = cursor.fetchall()
    conn.close()

    if not bookings:
        bot.send_message(message.chat.id, "🔍 Записів не знайдено")
        return

    text = f"🔍 Результати пошуку '{search_term}':\n\n"

    for booking_tuple in bookings:
        booking = get_booking_data(booking_tuple)
        if booking is None:
            continue

        try:
            date_formatted = datetime.datetime.strptime(booking['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
        except:
            date_formatted = booking['date']

        text += f"#{booking['id']} | {date_formatted} {booking['time']}\n"
        text += f"👤 {booking['first_name']} (@{booking['username']})\n"
        text += f"📞 {booking['phone']}\n"
        text += f"💅 {booking['service']} - {booking['price']}грн\n"

        # Додаємо кнопки для дій з записом
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            f"❌ Скасувати запис #{booking['id']}",
            callback_data=f"cancel_{booking['id']}"
        ))

        bot.send_message(message.chat.id, text, reply_markup=markup)
        text = ""


@bot.message_handler(func=lambda message: message.text == "📈 Статистика")
def statistics(message):
    if not is_admin(message.from_user.id):
        return

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()

    # Загальна кількість записів
    cursor.execute('SELECT COUNT(*) FROM bookings')
    total_bookings = cursor.fetchone()[0]

    # Загальний дохід
    cursor.execute('SELECT SUM(price) FROM bookings')
    total_revenue = cursor.fetchone()[0] or 0

    # Записи на сьогодні
    today = datetime.date.today().strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) FROM bookings WHERE date = ?', (today,))
    today_bookings = cursor.fetchone()[0]

    # Записи на завтра
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) FROM bookings WHERE date = ?', (tomorrow,))
    tomorrow_bookings = cursor.fetchone()[0]

    # Популярні послуги
    cursor.execute('''
        SELECT service, COUNT(*) as count 
        FROM bookings 
        GROUP BY service 
        ORDER BY count DESC 
        LIMIT 5
    ''')
    popular_services = cursor.fetchall()

    conn.close()

    text = f"""📈 СТАТИСТИКА

📊 Загальна кількість записів: {total_bookings}
💰 Загальний дохід: {total_revenue} грн
📅 Записи на сьогодні: {today_bookings}
🗓 Записи на завтра: {tomorrow_bookings}

🔥 Популярні послуги:
"""

    for service, count in popular_services:
        text += f"• {service}: {count} разів\n"

    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda message: message.text == "🗓 Календар записів")
def calendar_view(message):
    if not is_admin(message.from_user.id):
        return

    # Показуємо календар на поточний місяць
    today = datetime.date.today()
    show_calendar(message, today.year, today.month)


def show_calendar(message, year, month):
    # Створюємо календар
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]

    # Отримуємо кількість записів для кожного дня
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT date, COUNT(*) 
        FROM bookings 
        WHERE date LIKE ?
        GROUP BY date
    ''', (f'{year:04d}-{month:02d}-%',))

    bookings_count = dict(cursor.fetchall())
    conn.close()

    text = f"🗓 {month_name} {year}\n\n"
    text += "Пн Вт Ср Чт Пт Сб Нд\n"

    for week in cal:
        week_text = ""
        for day in week:
            if day == 0:
                week_text += "   "
            else:
                date_str = f'{year:04d}-{month:02d}-{day:02d}'
                count = bookings_count.get(date_str, 0)
                if count > 0:
                    week_text += f"{day:2d}*"
                else:
                    week_text += f"{day:2d} "
        text += week_text + "\n"

    text += "\n* - дні з записами"

    # Додаємо кнопки навігації
    markup = types.InlineKeyboardMarkup()

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    markup.add(
        types.InlineKeyboardButton("⬅️", callback_data=f"cal_{prev_year}_{prev_month}"),
        types.InlineKeyboardButton("➡️", callback_data=f"cal_{next_year}_{next_month}")
    )

    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cal_'))
def handle_calendar_navigation(call):
    if not is_admin(call.from_user.id):
        return

    _, year, month = call.data.split('_')
    year, month = int(year), int(month)

    # Оновлюємо календар
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT date, COUNT(*) 
        FROM bookings 
        WHERE date LIKE ?
        GROUP BY date
    ''', (f'{year:04d}-{month:02d}-%',))

    bookings_count = dict(cursor.fetchall())
    conn.close()

    text = f"🗓 {month_name} {year}\n\n"
    text += "Пн Вт Ср Чт Пт Сб Нд\n"

    for week in cal:
        week_text = ""
        for day in week:
            if day == 0:
                week_text += "   "
            else:
                date_str = f'{year:04d}-{month:02d}-{day:02d}'
                count = bookings_count.get(date_str, 0)
                if count > 0:
                    week_text += f"{day:2d}*"
                else:
                    week_text += f"{day:2d} "
        text += week_text + "\n"

    text += "\n* - дні з записами"

    # Оновлюємо кнопки навігації
    markup = types.InlineKeyboardMarkup()

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    markup.add(
        types.InlineKeyboardButton("⬅️", callback_data=f"cal_{prev_year}_{prev_month}"),
        types.InlineKeyboardButton("➡️", callback_data=f"cal_{next_year}_{next_month}")
    )

    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_'))
def handle_booking_cancellation(call):
    if not is_admin(call.from_user.id):
        return

    booking_id = call.data.split('_')[1]

    # Підтвердження скасування
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Так, скасувати", callback_data=f"confirm_cancel_{booking_id}"),
        types.InlineKeyboardButton("❌ Ні", callback_data="cancel_action")
    )

    bot.send_message(
        call.message.chat.id,
        f"Ви впевнені, що хочете скасувати запис #{booking_id}?",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_cancel_'))
def confirm_cancellation(call):
    booking_id = call.data.split('_')[2]

    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    if deleted:
        bot.edit_message_text(
            f"✅ Запис #{booking_id} успішно скасовано",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        bot.edit_message_text(
            f"❌ Запис #{booking_id} не знайдено",
            call.message.chat.id,
            call.message.message_id
        )


@bot.callback_query_handler(func=lambda call: call.data == 'cancel_action')
def cancel_action(call):
    bot.edit_message_text(
        "❌ Дію скасовано",
        call.message.chat.id,
        call.message.message_id
    )


def show_bookings_for_date(message, date, title):
    """Показує записи для конкретної дати"""
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM bookings 
        WHERE date = ? 
        ORDER BY time ASC
    ''', (date,))
    bookings = cursor.fetchall()
    conn.close()

    if not bookings:
        date_formatted = datetime.datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m.%Y')
        bot.send_message(message.chat.id, f"📭 {title} ({date_formatted}): записів немає")
        return

    date_formatted = datetime.datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m.%Y')
    text = f"📅 {title} ({date_formatted}):\n\n"

    total_revenue = 0

    for booking_tuple in bookings:
        booking = get_booking_data(booking_tuple)
        if booking is None:
            continue

        total_revenue += booking['price']

        text += f"🕐 {booking['time']} | #{booking['id']}\n"
        text += f"👤 {booking['first_name']}\n"
        text += f"📞 {booking['phone']}\n"
        text += f"💅 {booking['service']} - {booking['price']}грн\n"
        text += "─" * 25 + "\n"

    text += f"\n💰 Загальний дохід за день: {total_revenue} грн"
    text += f"\n📊 Кількість записів: {len(bookings)}"

    # Розбиваємо на частини якщо повідомлення занадто довге
    if len(text) > 4000:
        parts = [text[i:i + 4000] for i in range(0, len(text), 4000)]
        for part in parts:
            bot.send_message(message.chat.id, part)
    else:
        bot.send_message(message.chat.id, text)


# Обробка всіх інших повідомлень
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ У вас немає доступу до цього бота.")
        return

    bot.send_message(message.chat.id, "Використовуйте кнопки меню для навігації 👆")


if __name__ == '__main__':
    print("🔍 Перевірка структури бази даних...")
    column_count = check_table_structure()
    print(f"Знайдено колонок: {column_count}")

    print("Адмін бот запущено...")
    bot.infinity_polling()