import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

API_TOKEN = os.getenv("BOT_TOKEN")

# Подключение к Google Sheets
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
GOOGLE_CREDENTIALS = json.loads(GOOGLE_CREDENTIALS_JSON)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDENTIALS, scope)
gc = gspread.authorize(credentials)
spreadsheet_id = os.getenv("SPREADSHEET_ID")
sheet = gc.open_by_key(spreadsheet_id).sheet1

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Временная база пользователей
users_db = {}

# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🛍 Найти товар со скидкой"),
            KeyboardButton(text="📂 Категории товаров")
        ],
        [
            KeyboardButton(text="🔥 Топ скидок"),
            KeyboardButton(text="🔎 Найти товар по запросу")
        ],
        [
            KeyboardButton(text="🌐 Выбрать язык"),
            KeyboardButton(text="⚙️ О боте"),
            KeyboardButton(text="💬 Поддержка")
        ]
    ],
    resize_keyboard=True
)

# Inline меню категорий
categories_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📱 Смартфоны и гаджеты", callback_data="cat_phones")],
    [InlineKeyboardButton(text="👚 Одежда и обувь", callback_data="cat_clothes")],
    [InlineKeyboardButton(text="🎧 Электроника", callback_data="cat_electronics")],
    [InlineKeyboardButton(text="🍳 Товары для кухни", callback_data="cat_kitchen")],
    [InlineKeyboardButton(text="🛋 Товары для дома", callback_data="cat_home")],
    [InlineKeyboardButton(text="🧸 Детские товары", callback_data="cat_kids")],
    [InlineKeyboardButton(text="🏋️‍♂️ Спорт и отдых", callback_data="cat_sport")],
    [InlineKeyboardButton(text="💄 Красота и здоровье", callback_data="cat_beauty")],
    [InlineKeyboardButton(text="🎮 Игры и консоли", callback_data="cat_games")],
    [InlineKeyboardButton(text="🚗 Авто и мото", callback_data="cat_auto")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
])

# Обработчик команды /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users_db:
        users_db[user_id] = {
            'status': 'trial',
            'trial_start': datetime.now(),
            'trial_end': datetime.now() + timedelta(days=3)
        }
        await message.answer(
            "👋 Добро пожаловать в SaleHunterKz!\n\n"
            "🎉 3 дня бесплатного премиум-доступа активированы!",
            reply_markup=main_menu
        )
    else:
        await message.answer("Вы в главном меню:", reply_markup=main_menu)

# Обработчик кнопок главного меню
@dp.message()
async def menu_handler(message: types.Message):
    text = message.text
    if text == "🛍 Найти товар со скидкой":
        records = sheet.get_all_records()
        if records:
            for record in records:
                await message.answer(
                    f"📦 {record['Название товара']}\n"
                    f"🏷 Категория: {record['Категория']}\n"
                    f"💰 Старая цена: {record['Старая цена']}\n"
                    f"🔥 Новая цена: {record['Новая цена']}\n"
                    f"🎯 Скидка: {record['Скидка (%)']}\n"
                    f"🔗 [Перейти к товару]({record['Ссылка на товар']})\n"
                    f"📝 {record['Описание скидки']}",
                    parse_mode="Markdown"
                )
    elif text == "📂 Категории товаров":
        await message.answer("Выберите категорию:", reply_markup=categories_menu)

# Обработчик inline-кнопок категорий
@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    data = callback.data

    if data == "back_to_main":
        await callback.message.answer("Вы в главном меню:", reply_markup=main_menu)
        await callback.answer()

    elif data.startswith("cat_"):
        category_map = {
            "cat_phones": "Смартфоны и гаджеты",
            "cat_clothes": "Одежда и обувь",
            "cat_electronics": "Электроника",
            "cat_kitchen": "Товары для кухни",
            "cat_home": "Товары для дома",
            "cat_kids": "Детские товары",
            "cat_sport": "Спорт и отдых",
            "cat_beauty": "Красота и здоровье",
            "cat_games": "Игры и консоли",
            "cat_auto": "Авто и мото",
        }
        selected_category = category_map.get(data)
        if selected_category:
            records = sheet.get_all_records()
            found = False
            for record in records:
                if record['Категория'] == selected_category:
                    await callback.message.answer(
                        f"📦 {record['Название товара']}\n"
                        f"🏷 Категория: {record['Категория']}\n"
                        f"💰 Старая цена: {record['Старая цена']}\n"
                        f"🔥 Новая цена: {record['Новая цена']}\n"
                        f"🎯 Скидка: {record['Скидка (%)']}\n"
                        f"🔗 [Перейти к товару]({record['Ссылка на товар']})\n"
                        f"📝 {record['Описание скидки']}",
                        parse_mode="Markdown"
                    )
                    found = True
            if not found:
                await callback.message.answer(f"😔 В категории {selected_category} пока нет товаров.")

# Запуск бота через polling
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())


