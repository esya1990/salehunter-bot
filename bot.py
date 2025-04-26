import asyncio
import json
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Загружаем токен и данные из переменных окружения
API_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDS_JSON")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Подключение к Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDENTIALS_JSON), scope)
gc = gspread.authorize(credentials)
spreadsheet_id = '1nPcx56Y0FQ0Y0754BPuUp2i_zSjb1KW1N586PhsCNVY'
sheet = gc.open_by_key(spreadsheet_id).sheet1

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
            "🎉 Вам дарится 3 дня бесплатного премиум-доступа!\n\n"
            "Выбирайте действие ниже:",
            reply_markup=main_menu
        )
    else:
        await message.answer("Вы в главном меню:", reply_markup=main_menu)

# Обработчик кнопок главного меню
@dp.message()
async def menu_handler(message: types.Message):
    user_id = message.from_user.id
    user_data = users_db.get(user_id)

    # Проверка окончания пробного периода
    if not user_data or (user_data['status'] == 'trial' and datetime.now() > user_data['trial_end']):
        if message.text in ["🛍 Найти товар со скидкой", "🔥 Топ скидок", "📂 Категории товаров", "🔎 Найти товар по запросу"]:
            await message.answer("⏳ Ваш пробный период закончился. Для продолжения оформите подписку через @Yesnoyesno123.")
            return

    if message.text == "🛍 Найти товар со скидкой":
        records = sheet.get_all_records()
        if records:
            for record in records:
                text = (
                    f"📦 {record['Название товара']}\n"
                    f"🏷 Категория: {record['Категория']}\n"
                    f"💰 Старая цена: {record['Старая цена']}\n"
                    f"🔥 Новая цена: {record['Новая цена']}\n"
                    f"🎯 Скидка: {record['Скидка (%)']}\n"
                    f"🔗 [Перейти к товару]({record['Ссылка на товар']})\n"
                    f"📝 {record['Описание скидки']}\n"
                )
                await message.answer(text, parse_mode="Markdown")
        else:
            await message.answer("😔 Пока нет скидок в базе. Скоро обновим!")

    elif message.text == "📂 Категории товаров":
        await message.answer("Выберите категорию:", reply_markup=categories_menu)

    elif message.text == "⚙️ О боте":
        await message.answer("⚙️ SaleHunterKz - ваш помощник в поиске лучших скидок!\n🛍 Ежедневные обновления, топ предложения, лучшие цены!")

    elif message.text == "💬 Поддержка":
        await message.answer("📞 Нужна помощь? Пишите: @Yesnoyesno123")

    elif message.text == "🌐 Выбрать язык":
        await message.answer("🌍 Выбор языка скоро будет доступен!")

# Обработчик inline-кнопок
@dp.callback_query()
async def handle_callbacks(callback: types.CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id
    user_data = users_db.get(user_id)

    if data == "back_to_main":
        await callback.message.answer("Вы вернулись в главное меню:", reply_markup=main_menu)

    elif data.startswith("cat_"):
        if not user_data or (user_data['status'] == 'trial' and datetime.now() > user_data['trial_end']):
            await callback.message.answer("⏳ Ваш пробный период закончился. Для продолжения оформите подписку через @Yesnoyesno123.")
            return

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
                    text = (
                        f"📦 {record['Название товара']}\n"
                        f"🏷 Категория: {record['Категория']}\n"
                        f"💰 Старая цена: {record['Старая цена']}\n"
                        f"🔥 Новая цена: {record['Новая цена']}\n"
                        f"🎯 Скидка: {record['Скидка (%)']}\n"
                        f"🔗 [Перейти к товару]({record['Ссылка на товар']})\n"
                        f"📝 {record['Описание скидки']}\n"
                    )
                    await callback.message.answer(text, parse_mode="Markdown")
                    found = True
            if not found:
                await callback.message.answer(f"😔 Пока нет товаров в категории {selected_category}.")
        else:
            await callback.message.answer("Ошибка выбора категории.")

    await callback.answer()

# Веб-сервер для webhook
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

async def main():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    app.on_startup.append(on_startup)
    setup_application(app, dp)
    web.run_app(app, host="0.0.0.0", port=int(os.getenv('PORT', 8080)))

if __name__ == '__main__':
    asyncio.run(main())

