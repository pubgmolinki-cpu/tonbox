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
# Твой токен и ID
BOT_TOKEN = "8617831885:AAGTfZNkXdiLR9X69C0t7gpNwbeTkSwmkWc"
ADMIN_ID = 1866813859 

# ВАЖНО: Убедись, что здесь https:// (как в логах Render/Railway)
URL_SITE = "https://web-production-b5bd3.up.railway.app"

# Ссылка на базу данных из переменных окружения Railway
DATABASE_URL = os.environ.get("DATABASE_URL")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- РАБОТА С POSTGRESQL ---
def init_db():
    if not DATABASE_URL:
        logging.error("КРИТИЧЕСКАЯ ОШИБКА: DATABASE_URL не найдена в Variables!")
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
        logging.info("База данных PostgreSQL успешно инициализирована.")
    except Exception as e:
        logging.error(f"Не удалось подключиться к БД: {e}")

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
    cur.execute("INSERT INTO news (image_url, title, content) VALUES (%s, %s, %s)", 
                (image_url, title, content))
    conn.commit()
    cur.close()
    conn.close()

def delete_all_news():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("DELETE FROM news")
    conn.commit()
    cur.close()
    conn.close()

# Запуск создания таблицы
init_db()

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
    await message.answer("Добро пожаловать в TONBOX NEWS! Нажмите кнопку ниже, чтобы открыть ленту.", reply_markup=kb)

@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: Message, state: FSMContext):
    await message.answer("🛠 Режим создания новости. Пришлите ФОТО:")
    await state.set_state(NewPost.photo)

@dp.message(Command("del"), F.from_user.id == ADMIN_ID)
async def clear_news(message: Message):
    try:
        delete_all_news()
        await message.answer("✅ База данных полностью очищена!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при удалении: {e}")

@dp.message(NewPost.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_name = f"{uuid.uuid4()}.jpg"
    
    static_path = os.path.join(os.path.dirname(__file__), "static")
    if not os.path.exists(static_path): os.makedirs(static_path)
    
    await bot.download_file(file_info.file_path, os.path.join(static_path, file_name))
    await state.update_data(photo_url=f"/static/{file_name}")
    await message.answer("Отлично! Теперь введите заголовок новости:")
    await state.set_state(NewPost.title)

@dp.message(NewPost.title)
async def set_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("И последнее: введите текст новости:")
    await state.set_state(NewPost.content)

@dp.message(NewPost.content)
async def save_new_post(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        add_news(data['photo_url'], data['title'], message.text)
        await message.answer("✅ Новость успешно опубликована и сохранена в Postgres!")
    except Exception as e:
        await message.answer(f"❌ Ошибка сохранения в БД: {e}")
    await state.clear()

# --- ВЕБ-СЕРВЕР ---
async def handle_api(request):
    return web.json_response(get_news())

async def handle_site(request):
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type='text/html')
    except:
        return web.Response(text="Файл index.html не найден", status=404)

app = web.Application()
app.router.add_get('/', handle_site)
app.router.add_get('/api/news', handle_api)
app.router.add_static('/static/', path=os.path.join(os.path.dirname(__file__), "static"), name='static')

async def main():
    # Запуск бота и сервера параллельно
    asyncio.create_task(dp.start_polling(bot))
    
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Сервер запущен на порту {port}")
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
