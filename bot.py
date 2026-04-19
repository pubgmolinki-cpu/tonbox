import os
import logging
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# --- НАСТРОЙКИ (Railway Variables) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 1866813859
URL_SITE = os.environ.get("URL_SITE") # Например: https://your-app.railway.app
DATABASE_URL = os.environ.get("DATABASE_URL")
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
model = genai.GenerativeModel('gemini-1.5-flash')

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ---
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS teams (id SERIAL PRIMARY KEY, name TEXT UNIQUE, logo_url TEXT, division TEXT DEFAULT 'FTCL 3');
            CREATE TABLE IF NOT EXISTS players (id SERIAL PRIMARY KEY, team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE, name TEXT, rating INTEGER, goals INTEGER DEFAULT 0, assists INTEGER DEFAULT 0, avg_rating REAL DEFAULT 0.0);
            CREATE TABLE IF NOT EXISTS matches (id SERIAL PRIMARY KEY, tour INTEGER, home_id INTEGER REFERENCES teams(id), away_id INTEGER REFERENCES teams(id), score_home INTEGER, score_away INTEGER, stats JSONB);
            CREATE TABLE IF NOT EXISTS match_stats (id SERIAL PRIMARY KEY, match_id INTEGER REFERENCES matches(id) ON DELETE CASCADE, player_id INTEGER REFERENCES players(id), rating REAL, goals INTEGER, assists INTEGER, is_totw BOOLEAN DEFAULT FALSE);
        """)
        conn.commit()
        cur.close()
        conn.close()
        logging.info("✅ База TONSCORE готова.")
    except Exception as e:
        logging.error(f"Ошибка БД: {e}")

init_db()

# --- ЛОГИКА GEMINI ---
SYSTEM_PROMPT = """
Ты — ассистент TONSCORE. Ты анализируешь футбольные матчи.
1. Из 'Итогового протокола' вытаскивай статистику.
2. Формат: (Голы | Пасы | Отборы | Сейвы) | % | Оценка.
3. Оценку (напр. 82) всегда дели на 10 (8.2).
4. Если пользователь просит добавить команды или лого — подтверждай действие.
Будь кратким и профессиональным.
"""

# --- ХЕНДЛЕРЫ ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Продолжить", callback_data="menu")]
    ])
    await message.answer("<b>TONSCORE</b>\n\nДобро пожаловать в систему статистики FTCL!", parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data == "menu")
async def show_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Открыть TONSCORE (Web App)", web_app=WebAppInfo(url=URL_SITE))]
    ])
    await callback.message.edit_text("<b>FTCL 3</b>\nВыбери раздел в приложении:", parse_mode="HTML", reply_markup=kb)

@dp.message(F.from_user.id == ADMIN_ID)
async def admin_ai(message: Message):
    # Прямое общение с Gemini
    response = model.generate_content(f"{SYSTEM_PROMPT}\nЗапрос: {message.text}")
    await message.answer(f"🤖 <b>Gemini:</b>\n\n{response.text}", parse_mode="HTML")

# --- СЕРВЕР ДЛЯ WEB APP ---
async def handle_index(request):
    with open("index.html", "r", encoding="utf-8") as f:
        return web.Response(text=f.read(), content_type='text/html')

async def get_table(request):
    # Тестовые данные (позже заменим на SQL запрос)
    data = [{"name": "Ренти Сити", "points": 3}, {"name": "Зёльден", "points": 0}]
    return web.json_response(data)

app = web.Application()
app.router.add_get('/', handle_index)
app.router.add_get('/api/table', get_table)

async def main():
    asyncio.create_task(dp.start_polling(bot))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
