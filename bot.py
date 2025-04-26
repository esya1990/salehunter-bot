import asyncio
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from aiogram import web, Router

API_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/webhook"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET") or "supersecret"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 3000))

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Подключение к Google Sheets
CREDENTIALS_CONTENT = os.getenv("GOOGLE_CREDENTIALS_JSON")
CREDENTIALS_FILE = "credentials.json"

# Записываем ключ в файл если его нет
if CREDENTIALS_CONTENT and not os.path.exists(CREDENTIALS_FILE):
    with open(CREDENTIALS_FILE, "w") as f:
        f.write(CREDENTIALS_CONTENT)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
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
        "👋 Добро пожаловать в SaleHunterKz!",
        reply_markup=main_menu
    )

@dp.message()
async def menu_handler(message: types.Message):
    if message.text == "🛍 Найти товар со скидкой":
        records = sheet.get_all_records()
        if records:
            for record in records:
                text = (
                    f"📦 {record['Название товара']}\n"
                    f"🏷 Категория: {record['Категория']}\n"
                    f"💰 Старая цена: {record['Старая цена']}\n"
                    f"🔥 Новая цена: {record['Новая цена']}\n"
                    f"🌟 Скидка: {record['Скидка (%)']}\n"
                    f"🔗 [Перейти к товару]({record['Ссылка на товар']})\n"
                    f"📝 {record['Описание скидки']}"
                )
                await message.answer(text, parse_mode="Markdown")
        else:
            await message.answer("😔 Пока нет скидок в базе.")
    elif message.text == "📂 Категории товаров":
        await message.answer("Выберите категорию:", reply_markup=categories_menu)

@dp.callback_query()
async def handle_callbacks(callback: types.CallbackQuery):
    data = callback.data

    if data == "back_to_main":
        await callback.message.answer("Вы вернулись в главное меню:", reply_markup=main_menu)
    elif data.startswith("cat_"):
        selected_category = {
            "cat_phones": "Смартфоны и гаджеты",
            "cat_clothes": "Одежда и обувь",
            "cat_electronics": "Электроника",
            "cat_kitchen": "Товары для кухни",
            "cat_home": "Товары для дома",
            "cat_kids": "Детские товары",
            "cat_sport": "Спорт и отдых",
            "cat_beauty": "Красота и здоровье",
            "cat_games": "Игры и консоли",
            "cat_auto": "Авто и мото"
        }.get(data)

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
                        f"🌟 Скидка: {record['Скидка (%)']}\n"
                        f"🔗 [Перейти к товару]({record['Ссылка на товар']})\n"
                        f"📝 {record['Описание скидки']}"
                    )
                    await callback.message.answer(text, parse_mode="Markdown")
                    found = True
            if not found:
                await callback.message.answer(f"😔 Пока нет товаров в категории {selected_category}.")
        else:
            await callback.message.answer("Ошибка выбора категории.")

    await callback.answer()

async def on_startup(bot: Bot) -> None:
    webhook_url = os.getenv("RENDER_EXTERNAL_URL") + WEBHOOK_PATH
    await bot.set_webhook(webhook_url, secret_token=WEBHOOK_SECRET)

async def on_shutdown(bot: Bot) -> None:
    await bot.delete_webhook()

app = web.Application()
app.router.add_webhook(path=WEBHOOK_PATH, dispatcher=dp, bot=bot, secret_token=WEBHOOK_SECRET)

if __name__ == '__main__':
    web.run_app(
        app,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
        startup=on_startup,
        shutdown=on_shutdown
    )

