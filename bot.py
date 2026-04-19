import asyncio
import os
import logging
import uuid
import psycopg2
import aiohttp
import base64
from psycopg2.extras import RealDictCursor
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8613728108:AAGR9Lmdx2YvG6wbg8qk31rcLxeKD4Vu6Po"
ADMIN_ID = 1866813859 
URL_SITE = "https://web-production-b5bd3.up.railway.app"
DATABASE_URL = os.environ.get("DATABASE_URL")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ФУНКЦИЯ ЗАГРУЗКИ НА IMGBB ---
async def upload_to_imgbb(image_bytes: bytes):
    if not IMGBB_API_KEY:
        logging.error("IMGBB_API_KEY не установлен!")
        return None
    
    url = "https://api.imgbb.com/1/upload"
    data = {
        "key": IMGBB_API_KEY,
        "image": base64.b64encode(image_bytes).decode("utf-8")
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as response:
            if response.status == 200:
                result = await response.json()
                return result["data"]["url"] # Возвращает прямую ссылку на фото
            else:
                logging.error(f"Ошибка ImgBB: {await response.text()}")
                return None

# --- РАБОТА С БД ---
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_db_connection()
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

def add_news(image_url, title, content):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO news (image_url, title, content) VALUES (%s, %s, %s)", 
                (image_url, title, content))
    conn.commit()
    cur.close()
    conn.close()

def get_news():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT image_url, title, content, id FROM news ORDER BY created_at DESC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except: return []

init_db()

# --- СОСТОЯНИЯ ---
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
    await message.answer("Добро пожаловать в TONBOX NEWS!", reply_markup=kb)

@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: Message, state: FSMContext):
    await message.answer("🛠 Пришлите ФОТО для новости:")
    await state.set_state(NewPost.photo)

@dp.message(Command("del"), F.from_user.id == ADMIN_ID)
async def clear_news(message: Message):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM news")
    conn.commit()
    cur.close()
    conn.close()
    await message.answer("✅ База очищена!")

@dp.message(NewPost.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    msg = await message.answer("⏳ Загружаю фото в облако...")
    
    # Получаем байты фото из Телеграма
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    photo_bytes = await bot.download_file(file_info.file_path)
    
    # Грузим на ImgBB
    img_url = await upload_to_imgbb(photo_bytes.read())
    
    if img_url:
        await state.update_data(photo_url=img_url)
        await msg.edit_text("✅ Фото сохранено в облаке! Введите ЗАГОЛОВОК:")
        await state.set_state(NewPost.title)
    else:
        await msg.edit_text("❌ Ошибка загрузки фото. Попробуйте еще раз.")

@dp.message(NewPost.title)
async def set_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите ТЕКСТ новости:")
    await state.set_state(NewPost.content)

@dp.message(NewPost.content)
async def save_post(message: Message, state: FSMContext):
    data = await state.get_data()
    add_news(data['photo_url'], data['title'], message.text)
    await message.answer("✅ Новость опубликована навсегда!")
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

async def main():
    asyncio.create_task(dp.start_polling(bot))
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', port).start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
