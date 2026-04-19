import os
import logging
import asyncio
import psycopg2
import json
from psycopg2.extras import RealDictCursor
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# --- НАСТРОЙКИ (КЛЮЧ ВПИСАН НАПРЯМУЮ) ---
GEMINI_KEY = "AIzaSyBTfuFyYRnZBjm9WLJUpQuqOZ7fbNk-70o"
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 1866813859
URL_SITE = os.environ.get("URL_SITE") 
DATABASE_URL = os.environ.get("DATABASE_URL")

# Настройка Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
def init_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS teams (id SERIAL PRIMARY KEY, name TEXT UNIQUE, logo_url TEXT);
            CREATE TABLE IF NOT EXISTS players (id SERIAL PRIMARY KEY, team_id INTEGER, name TEXT, goals INTEGER DEFAULT 0, assists INTEGER DEFAULT 0, rating REAL DEFAULT 0.0);
            CREATE TABLE IF NOT EXISTS matches (id SERIAL PRIMARY KEY, home_team TEXT, away_team TEXT, score_home INTEGER, score_away INTEGER);
        """)
        conn.commit()
        cur.close()
        conn.close()
        logging.info("✅ База данных подключена")
    except Exception as e:
        logging.error(f"❌ Ошибка БД: {e}")

# --- ХЕНДЛЕРЫ ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="TonScore", web_app=WebAppInfo(url=URL_SITE))]
    ])
    await message.answer("TonScore доступен уже в этом мини приложении", reply_markup=kb)

@dp.message(F.from_user.id == ADMIN_ID)
async def admin_ai(message: Message):
    await bot.send_chat_action(message.chat.id, "typing")
    try:
        # Простой запрос к ИИ без лишних нагромождений
        response = model.generate_content(f"Ты ассистент TonScore. Ответь кратко: {message.text}")
        await message.answer(f"🤖 {response.text}")
    except Exception as e:
        logging.error(f"Ошибка Gemini: {e}")
        await message.answer("⚠️ ИИ пока не отвечает. Проверь логи в Railway.")

# --- СЕРВЕР ---
async def handle_index(request):
    with open("index.html", "r", encoding="utf-8") as f:
        return web.Response(text=f.read(), content_type='text/html')

app = web.Application()
app.router.add_get('/', handle_index)

async def main():
    init_db()
    asyncio.create_task(dp.start_polling(bot))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
