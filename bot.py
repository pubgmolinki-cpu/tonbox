import asyncio
import os
import logging
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8617831885:AAGTfZNkXdiLR9X69C0t7gpNwbeTkSwmkWc"
ADMIN_ID = 1866813859 
URL_SITE = "https://web-production-b5bd3.up.railway.app"
DATABASE_URL = os.environ.get("DATABASE_URL")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ПРОВЕРКА И СОЗДАНИЕ ПАПОК ---
STATIC_PATH = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_PATH):
    os.makedirs(STATIC_PATH)
    logging.info("Папка static создана автоматически")

# --- РАБОТА С БД ---
def init_db():
    if not DATABASE_URL:
        logging.error("!!! КРИТИЧЕСКАЯ ОШИБКА: DATABASE_URL не найдена в Variables !!!")
        return
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id SERIAL PRIMARY KEY,
                image_url TEXT,
                title TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logging.error(f"Ошибка БД: {e}")

def get_news():
    if not DATABASE_URL: return []
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT image_url, title, content, id FROM news ORDER BY created_at DESC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except:
        return []

def add_news(image_url, title, content):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("INSERT INTO news (image_url, title, content) VALUES (%s, %s, %s)", (image_url, title, content))
    conn.commit()
    cur.close()
    conn.close()

init_db()

class NewPost(StatesGroup):
    photo = State()
    title = State()
    content = State()

# --- КОМАНДЫ ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Смотреть Новости! ⚽️", web_app=WebAppInfo(url=URL_SITE))]
    ])
    await message.answer("Добро пожаловать!", reply_markup=kb)

@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: Message, state: FSMContext):
    await message.answer("Пришли фото для новости:")
    await state.set_state(NewPost.photo)

@dp.message(NewPost.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_name = f"{uuid.uuid4()}.jpg"
    await bot.download_file(file_info.file_path, os.path.join(STATIC_PATH, file_name))
    await state.update_data(photo_url=f"/static/{file_name}")
    await message.answer("Введите заголовок:")
    await state.set_state(NewPost.title)

@dp.message(NewPost.title)
async def set_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите описание:")
    await state.set_state(NewPost.content)

@dp.message(NewPost.content)
async def save_post(message: Message, state: FSMContext):
    data = await state.get_data()
    add_news(data['photo_url'], data['title'], message.text)
    await message.answer("✅ Готово!")
    await state.clear()

# --- СЕРВЕР ---
async def handle_api(request):
    return web.json_response(get_news())

async def handle_site(request):
    with open("index.html", "r", encoding="utf-8") as f:
        return web.Response(text=f.read(), content_type='text/html')

app = web.Application()
app.router.add_get('/', handle_site)
app.router.add_get('/api/news', handle_api)
# Раздаем статику только если папка существует
app.router.add_static('/static/', path=STATIC_PATH, name='static')

async def main():
    asyncio.create_task(dp.start_polling(bot))
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', port).start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
