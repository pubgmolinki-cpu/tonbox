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

# Получаем DATABASE_URL из системы
DATABASE_URL = os.environ.get("DATABASE_URL")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Создаем папку static для картинок
STATIC_PATH = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_PATH):
    os.makedirs(STATIC_PATH)

def get_db_connection():
    # Если переменная пустая, пытаемся взять её еще раз напрямую
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logging.error("КРИТИЧЕСКАЯ ОШИБКА: DATABASE_URL всё еще пуста!")
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
        logging.info("База данных PostgreSQL успешно инициализирована")
    except Exception as e:
        logging.error(f"Не удалось подключиться к БД: {e}")

# Инициализация при старте
init_db()

# --- ВСЁ ОСТАЛЬНОЕ (ADMIN, DEL, API) ОСТАЕТСЯ КАК БЫЛО ---
# (Просто вставь сюда функции из предыдущего сообщения)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Смотреть Новости! ⚽️", web_app=WebAppInfo(url=URL_SITE))]
    ])
    await message.answer("Добро пожаловать!", reply_markup=kb)

# ... (Остальные хендлеры /admin, /del и т.д. без изменений)

async def handle_api(request):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT image_url, title, content, id FROM news ORDER BY created_at DESC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return web.json_response(rows)
    except:
        return web.json_response([])

async def handle_site(request):
    with open("index.html", "r", encoding="utf-8") as f:
        return web.Response(text=f.read(), content_type='text/html')

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
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
