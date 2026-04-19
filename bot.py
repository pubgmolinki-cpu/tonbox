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

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Создаем папку для картинок
STATIC_PATH = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_PATH):
    os.makedirs(STATIC_PATH)

# --- ФУНКЦИИ БАЗЫ ДАННЫХ ---
def get_db_connection():
    # Берем ссылку на базу напрямую из переменных Railway
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logging.error("КРИТИЧЕСКАЯ ОШИБКА: DATABASE_URL не найдена!")
        raise ValueError("DATABASE_URL is missing!")
    return psycopg2.connect(db_url)

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
        logging.info("База данных успешно инициализирована.")
    except Exception as e:
        logging.error(f"Ошибка БД при старте: {e}")

def get_news():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT image_url, title, content, id FROM news ORDER BY created_at DESC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except:
        return []

def add_news(image_url, title, content):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO news (image_url, title, content) VALUES (%s, %s, %s)", 
                (image_url, title, content))
    conn.commit()
    cur.close()
    conn.close()

def delete_all_news_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM news")
    conn.commit()
    cur.close()
    conn.close()

# Запуск проверки БД
init_db()

# --- СОСТОЯНИЯ (FSM) ---
class NewPost(StatesGroup):
    photo = State()
    title = State()
    content = State()

# --- ХЕНДЛЕРЫ БОТА ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Смотреть Новости! ⚽️", web_app=WebAppInfo(url=URL_SITE))]
    ])
    await message.answer("Добро пожаловать в TONBOX NEWS!", reply_markup=kb)

# КОМАНДА /admin [восстановлено]
@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: Message, state: FSMContext):
    await message.answer("🛠 Режим создания новости. Пришлите ФОТО (сжатое):")
    await state.set_state(NewPost.photo)

# КОМАНДА /del [восстановлено]
@dp.message(Command("del"), F.from_user.id == ADMIN_ID)
async def clear_news(message: Message):
    try:
        delete_all_news_db()
        await message.answer("✅ База данных успешно очищена!")
    except Exception as e:
        await message.answer(f"❌ Ошибка удаления: {e}")

@dp.message(NewPost.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_name = f"{uuid.uuid4()}.jpg"
    
    await bot.download_file(file_info.file_path, os.path.join(STATIC_PATH, file_name))
    await state.update_data(photo_url=f"/static/{file_name}")
    await message.answer("Отлично! Теперь введите ЗАГОЛОВОК новости:")
    await state.set_state(NewPost.title)

@dp.message(NewPost.title)
async def set_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("И последнее: введите ТЕКСТ новости:")
    await state.set_state(NewPost.content)

@dp.message(NewPost.content)
async def save_new_post(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        # Сохранение в PostgreSQL
        add_news(data['photo_url'], data['title'], message.text)
        await message.answer("✅ Новость опубликована!")
    except Exception as e:
        await message.answer(f"❌ Ошибка сохранения в базу: {e}")
    await state.clear()

# --- ВЕБ-СЕРВЕР ---
async def handle_api(request):
    return web.json_response(get_news())

async def handle_site(request):
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type='text/html')
    return web.Response(text="index.html not found", status=404)

app = web.Application()
app.router.add_get('/', handle_site)
app.router.add_get('/api/news', handle_api)
app.router.add_static('/static/', path=STATIC_PATH, name='static')

async def main():
    asyncio.create_task(dp.start_polling(bot))
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', port).start()
    logging.info(f"Сервер запущен на порту {port}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
