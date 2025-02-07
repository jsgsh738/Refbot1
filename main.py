import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.markdown import hbold
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime

TOKEN = "7910975290:AAF99SgbTc6Gx3y4u49nYZEewh5ZU7_lQTk"
CHANNEL_ID = "@Agnihachannel"
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
    firecoins INTEGER DEFAULT 0, 
    last_bonus INTEGER DEFAULT 0,
    referrer INTEGER
)
""")
conn.commit()

# 🚀 Проверка подписки
async def check_subscription(user_id):
    try:
        chat_member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except TelegramBadRequest:
        return False

# 🔥 Главное меню
async def main_menu(message):
    user_id = message.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🎁 Получить бонус", callback_data="get_bonus")],
        [InlineKeyboardButton(text="🏆 Топ пользователей", callback_data="top_users")],
        [InlineKeyboardButton(text="🛍 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="🔗 Пригласить друзей", callback_data="referral")]
    ])
    await message.answer(f"🔥 Добро пожаловать!\n💰 Твой баланс: {get_firecoins(user_id)} 🔥\n\nВыбери действие:", 
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
        cursor.execute("INSERT INTO users (user_id, username, firecoins, referrer) VALUES (?, ?, ?, ?)",
                       (user_id, username, 0, referrer_id))
        conn.commit()

        if referrer_id and referrer_id.isdigit():
            cursor.execute("UPDATE users SET firecoins = firecoins + 2 WHERE user_id = ?", (int(referrer_id),))
            conn.commit()

    if not await check_subscription(user_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Подписаться!", url=f"https://t.me/{CHANNEL_ID[1:]}")],
            [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")]
        ])
        await message.answer("🔥 Чтобы пользоваться ботом, подпишись на канал!", reply_markup=keyboard)
    else:
        await main_menu(message)

# ✅ Проверка подписки
@dp.callback_query(lambda call: call.data == "check_sub")
async def check_subscription_callback(call: types.CallbackQuery):
    user_id = call.from_user.id
    if await check_subscription(user_id):
        await main_menu(call.message)
    else:
        await call.answer("❌ Ты не подписался!", show_alert=True)

# 👤 Профиль
@dp.callback_query(lambda call: call.data == "profile")
async def profile(call: types.CallbackQuery):
    user_id = call.from_user.id
    username = call.from_user.username or "Без ника"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton(text="🛍 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]  # Теперь кнопка работает!
    ])

    await call.message.edit_text(f"👤 {hbold(username)}, вот твой профиль:\n"
                                 f"💰 Баланс: {get_firecoins(user_id)} 🔥", reply_markup=keyboard)

# 🏆 Топ пользователей
@dp.callback_query(lambda call: call.data == "top_users")
async def top_users(call: types.CallbackQuery):
    cursor.execute("SELECT username, firecoins FROM users ORDER BY firecoins DESC LIMIT 10")
    top = cursor.fetchall()
    text = "🔥 <b>Топ-10 пользователей:</b>\n"
    for i, (username, firecoins) in enumerate(top, start=1):
        text += f"{i}. {hbold(username)} — {firecoins} 🔥\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]  # Теперь кнопка работает!
    ])
    await call.message.edit_text(text, reply_markup=keyboard)

# 🔗 Реферальная ссылка
@dp.callback_query(lambda call: call.data == "referral")
async def referral(call: types.CallbackQuery):
    user_id = call.from_user.id
    bot_username = (await bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user_id}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]  # Теперь кнопка работает!
    ])

    await call.message.edit_text(f"🔗 Твоя реферальная ссылка:\n{link}", reply_markup=keyboard)

# 🛍 Магазин
@dp.callback_query(lambda call: call.data == "shop")
async def shop(call: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]  # Теперь кнопка работает!
    ])
    await call.message.edit_text("🛍 Пока что нет товаров! Скоро появятся!", reply_markup=keyboard)

# 🔙 Назад в главное меню
@dp.callback_query(lambda call: call.data == "main_menu")
async def back_to_main(call: types.CallbackQuery):
    await main_menu(call.message)

# 🚀 Запуск бота
async def main():
    await dp.start_polling(bot)

def get_firecoins(user_id):
    cursor.execute("SELECT firecoins FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()[0] or 0

if __name__ == "__main__":
    asyncio.run(main())

import asyncio

async def keep_alive():
    while True:
        await asyncio.sleep(3600)  # Бот будет ждать 1 час в бесконечном цикле

if __name__ == "__main__":
    asyncio.create_task(keep_alive())  # Запускаем бесконечный цикл
    asyncio.run(main())  # Запускаем бота

