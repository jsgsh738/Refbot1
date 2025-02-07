import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.markdown import hbold
from datetime import datetime
from keep_alive import keep_alive  # Поддержка работы на Render

TOKEN = "7926852495:AAFVySjZVau5_sxafIPKMeBRDFmehiIbDxI"
BONUS_INTERVAL = 6 * 60 * 60  # 6 часов

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Подключение к БД
conn = sqlite3.connect("firecoins.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY, 
    username TEXT, 
    ma3coins INTEGER DEFAULT 0, 
    last_bonus INTEGER DEFAULT 0,
    referrer INTEGER
)
""")
conn.commit()

# 🔥 Главное меню
async def main_menu(call):
    user_id = call.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🎁 Получить бонус", callback_data="get_bonus")],
        [InlineKeyboardButton(text="🏆 Топ пользователей", callback_data="top_users")],
        [InlineKeyboardButton(text="🛍 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="🔗 Пригласить друзей", callback_data="referral")]
    ])
    await call.message.edit_text(f"💎 Добро пожаловать!\n💰 Твой баланс: {get_ma3coins(user_id)} Ma3coin\n\nВыбери действие:", 
                                 reply_markup=keyboard)

# 🔥 Старт
@dp.message(CommandStart())
async def start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Без ника"
    referrer_id = message.text.split()[-1] if len(message.text.split()) > 1 else None

    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    user_exists = cursor.fetchone()

    if not user_exists:
        cursor.execute("INSERT INTO users (user_id, username, ma3coins, referrer) VALUES (?, ?, ?, ?)",
                       (user_id, username, 0, referrer_id))
        conn.commit()

        if referrer_id and referrer_id.isdigit():
            cursor.execute("UPDATE users SET ma3coins = ma3coins + 2 WHERE user_id = ?", (int(referrer_id),))
            conn.commit()

    await main_menu(message)

# 👤 Профиль
@dp.callback_query(lambda call: call.data == "profile")
async def profile(call: types.CallbackQuery):
    user_id = call.from_user.id
    username = call.from_user.username or "Без ника"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton(text="🛍 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

    await call.message.edit_text(f"👤 {hbold(username)}, вот твой профиль:\n"
                                 f"💰 Баланс: {get_ma3coins(user_id)} Ma3coin", reply_markup=keyboard)

# 🔙 Назад в главное меню
@dp.callback_query(lambda call: call.data == "back_to_main")
async def back_to_main(call: types.CallbackQuery):
    await main_menu(call)

# 🏆 Топ пользователей
@dp.callback_query(lambda call: call.data == "top_users")
async def top_users(call: types.CallbackQuery):
    cursor.execute("SELECT username, ma3coins FROM users ORDER BY ma3coins DESC LIMIT 10")
    top = cursor.fetchall()
    text = "💎 <b>Топ-10 пользователей:</b>\n"
    for i, (username, ma3coins) in enumerate(top, start=1):
        text += f"{i}. {hbold(username)} — {ma3coins} Ma3coin\n"
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]]
    ))

# 🔗 Реферальная ссылка (теперь отправляется сообщением)
@dp.callback_query(lambda call: call.data == "referral")
async def referral(call: types.CallbackQuery):
    user_id = call.from_user.id
    bot_username = (await bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user_id}"
    await call.message.answer(f"🔗 Твоя реферальная ссылка:\n{link}")

# 🛍 Магазин
@dp.callback_query(lambda call: call.data == "shop")
async def shop(call: types.CallbackQuery):
    await call.message.edit_text("🛍 Пока что нет товаров! Скоро появятся!", 
                                 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                     [InlineKeyboardButton(text="🔙 Назад", callback_data="profile")]
                                 ]))

# 🎁 Получение бонуса
@dp.callback_query(lambda call: call.data == "get_bonus")
async def claim_bonus(call: types.CallbackQuery):
    user_id = call.from_user.id
    cursor.execute("SELECT last_bonus FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    last_bonus = row[0] if row else 0

    now = int(datetime.now().timestamp())
    if last_bonus and now - last_bonus < BONUS_INTERVAL:
        remaining = BONUS_INTERVAL - (now - last_bonus)
        hours, minutes = divmod(remaining // 60, 60)
        await call.answer(f"⏳ Бонус уже получен! Приходи через {hours}ч {minutes}м.", show_alert=True)
    else:
        cursor.execute("UPDATE users SET ma3coins = ma3coins + 3, last_bonus = ? WHERE user_id = ?", (now, user_id))
        conn.commit()
        await call.answer("🎉 Ты получил +3 Ma3coin!", show_alert=True)

# 🚀 Запуск бота
async def main():
    await dp.start_polling(bot)

def get_ma3coins(user_id):
    cursor.execute("SELECT ma3coins FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

import asyncio

async def keep_alive():
    while True:
        await asyncio.sleep(3600)  # Бот будет ждать 1 час в бесконечном цикле

if __name__ == "__main__":
    asyncio.create_task(keep_alive())  # Запускаем бесконечный цикл
    asyncio.run(main())  # Запускаем бота

