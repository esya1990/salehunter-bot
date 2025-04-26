import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

API_TOKEN = '7531893339:AAEveLuB5grak6VHu78enCPJDwWWkCi0E8c'
ADMIN_ID = 5473537631

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Подключение к Google Sheets
CREDENTIALS_FILE = 'honestalmatybot-b81f425fb588.json'
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
gc = gspread.authorize(credentials)
spreadsheet_id = '1nPcx56Y0FQ0Y0754BPuUp2i_zSjb1KW1N586PhsCNVY'
sheet = gc.open_by_key(spreadsheet_id).sheet1

# База пользователей
users_db = {}

# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛍 Найти товар со скидкой"), KeyboardButton(text="📂 Категории товаров")],
        [KeyboardButton(text="🔥 Топ скидок"), KeyboardButton(text="🔎 Найти товар по запросу")],
        [KeyboardButton(text="🌐 Выбрать язык"), KeyboardButton(text="⚙️ О боте"), KeyboardButton(text="💬 Поддержка")]
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

# Inline фильтрация скидок
discount_filter_menu = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🔖 До 50%", callback_data="discount_50"),
        InlineKeyboardButton(text="🔖 60%", callback_data="discount_60"),
        InlineKeyboardButton(text="🔖 70%", callback_data="discount_70")
    ],
    [
        InlineKeyboardButton(text="🔖 80%", callback_data="discount_80"),
        InlineKeyboardButton(text="🔖 90%", callback_data="discount_90"),
        InlineKeyboardButton(text="🔖 95%", callback_data="discount_95")
    ]
])

# FSM состояния
class SearchStates(StatesGroup):
    waiting_for_query = State()

# Проверка премиума или активного триала
def is_premium(user_id):
    user = users_db.get(user_id)
    if not user:
        return False
    if user['status'] == 'premium':
        return True
    if user['status'] == 'trial' and user['trial_end'] > datetime.now():
        return True
    return False

# Отправка карточки товара
async def send_product(target, record):
    text = (
        f"📦 {record['Название товара']}\n"
        f"🏷 Категория: {record['Категория']}\n"
        f"💰 Старая цена: {record['Старая цена']}\n"
        f"🔥 Новая цена: {record['Новая цена']}\n"
        f"🎯 Скидка: {record['Скидка (%)']}\n"
        f"🔗 [Перейти к товару]({record['Ссылка на товар']})\n"
        f"📝 {record['Описание скидки']}"
    )
    await target.answer(text, parse_mode="Markdown")

# Команда /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users_db:
        users_db[user_id] = {'status': 'trial', 'trial_start': datetime.now(), 'trial_end': datetime.now() + timedelta(days=3)}
    await message.answer("Добро пожаловать в SaleHunterKz!", reply_markup=main_menu)

# 👉 /premium
@dp.message(F.text.startswith("/premium"))
async def give_premium(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет прав.")
        return
    try:
        parts = message.text.split()
        target_id = int(parts[1])
        if target_id not in users_db:
            users_db[target_id] = {}
        users_db[target_id]['status'] = 'premium'
        await message.answer(f"✅ Премиум доступ выдан пользователю {target_id}!")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

# Обработчик поиска
@dp.message(SearchStates.waiting_for_query)
async def process_search(message: types.Message, state: FSMContext):
    query = message.text.lower()
    records = sheet.get_all_records()
    found = False
    for record in records:
        if query in record['Название товара'].lower():
            await send_product(message, record)
            found = True
    if not found:
        await message.answer("Ничего не найдено по запросу.")
    await state.clear()

# Главное меню
@dp.message()
async def main_menu_handler(message: types.Message, state: FSMContext):
    text = message.text
    if text == "🛍 Найти товар со скидкой":
        records = sheet.get_all_records()
        for record in records:
            await send_product(message, record)
    elif text == "📂 Категории товаров":
        await message.answer("Выберите категорию:", reply_markup=categories_menu)
    elif text == "🔎 Найти товар по запросу":
        await message.answer("Введите название товара для поиска:")
        await state.set_state(SearchStates.waiting_for_query)
    elif text == "🔥 Топ скидок":
        await message.answer("Выберите скидку:", reply_markup=discount_filter_menu)
    elif text == "🌐 Выбрать язык":
        await message.answer("🌍 Выбор языка скоро будет доступен!")
    elif text == "⚙️ О боте":
        await message.answer("⚙️ SaleHunterKz - ваш помощник в поиске лучших скидок!\n🛍 Ежедневные обновления, топ предложения, лучшие цены!")
    elif text == "💬 Поддержка":
        support_button = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="💬 Связаться с поддержкой", url="https://t.me/Yesnoyesno123")]]
        )
        await message.answer("📞 Нужна помощь? Нажмите кнопку ниже, чтобы написать в поддержку:", reply_markup=support_button)
    else:
        await message.answer("Пожалуйста, выберите действие из меню.")

# Фильтрация по скидке
@dp.callback_query(F.data.startswith("discount_"))
async def discount_filter(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    records = sheet.get_all_records()
    found = False

    selected_discount = int(callback.data.split('_')[1])

    if selected_discount == 50:
        for record in records:
            discount_value = int(record['Скидка (%)'].replace('%', ''))
            if discount_value <= 50:
                await send_product(callback.message, record)
                found = True
    else:
        if not is_premium(user_id):
            await callback.message.answer("⏳ Для просмотра скидок выше 50% нужна премиум подписка. Свяжитесь с поддержкой: @Yesnoyesno123")
            await callback.answer()
            return
        for record in records:
            discount_value = int(record['Скидка (%)'].replace('%', ''))
            if discount_value >= selected_discount:
                await send_product(callback.message, record)
                found = True

    if not found:
        await callback.message.answer("😔 Пока нет товаров с такими скидками. Следите за обновлениями!")

    await callback.answer()

# Категории
@dp.callback_query()
async def category_filter(callback: types.CallbackQuery):
    data = callback.data
    if data == "back_to_main":
        await callback.message.answer("Главное меню:", reply_markup=main_menu)
        await callback.answer()
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
    selected = category_map.get(data)
    if selected:
        records = sheet.get_all_records()
        for record in records:
            if record['Категория'] == selected:
                await send_product(callback.message, record)
    await callback.answer()

# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
