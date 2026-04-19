import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8617831885:AAGuiDHofe7tvx0QwS8xJfcNhO-TkfCduOA"
ADMIN_ID = 1866813859  # Узнай у @userinfobot
URL_SITE = "http://o964180m.beget.tech/"
DB_PATH = "news.db" # Путь к файлу базы на хостинге

bot = Bot(token=TOKEN)
dp = Dispatcher()

class NewPost(StatesGroup):
    photo_url = State()
    title = State()
    content = State()

# Создаем таблицу в базе, если её нет
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS news 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      image_url TEXT, title TEXT, content TEXT)''')
    conn.commit()
    conn.close()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть новости ⚽️", web_app=WebAppInfo(url=URL_SITE))]
    ])
    await message.answer("Добро пожаловать в FTCL 3 News!", reply_markup=kb)

@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: Message, state: FSMContext):
    await message.answer("🛠 Админка: Отправь прямую ССЫЛКУ на фото новости (или загрузи фото в imgur):")
    await state.set_state(NewPost.photo_url)

@dp.message(NewPost.photo_url)
async def set_photo(message: Message, state: FSMContext):
    await state.update_data(photo_url=message.text)
    await message.answer("Введите ЗАГОЛОВОК новости:")
    await state.set_state(NewPost.title)

@dp.message(NewPost.title)
async def set_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите ТЕКСТ новости:")
    await state.set_state(NewPost.content)

@dp.message(NewPost.content)
async def save_news(message: Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO news (image_url, title, content) VALUES (?, ?, ?)",
                   (data['photo_url'], data['title'], message.text))
    conn.commit()
    conn.close()
    await message.answer("✅ Новость опубликована на сайте!")
    await state.clear()

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
