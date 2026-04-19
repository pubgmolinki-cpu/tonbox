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

# --- НАСТРОЙКИ ---
# Вставь сюда свой ключ вручную, если в Railway Variables он не подхватывается
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyBTfuFyYRmZBjm9WLJUpQuqOZ7fbNk-70o")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 1866813859
URL_SITE = os.environ.get("URL_SITE") 
DATABASE_URL = os.environ.get("DATABASE_URL")

genai.configure(api_key=GEMINI_KEY)
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
model = genai.GenerativeModel('gemini-1.5-flash')

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
def init_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        # Таблицы для твоей структуры: Клубы, Игроки, Матчи, Статистика
        cur.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id SERIAL PRIMARY KEY, 
                name TEXT UNIQUE, 
                logo_url TEXT DEFAULT 'https://via.placeholder.com/100'
            );
            CREATE TABLE IF NOT EXISTS players (
                id SERIAL PRIMARY KEY, 
                team_id INTEGER REFERENCES teams(id), 
                name TEXT, 
                position TEXT,
                goals INTEGER DEFAULT 0, 
                assists INTEGER DEFAULT 0, 
                saves INTEGER DEFAULT 0, 
                tackles INTEGER DEFAULT 0,
                rating REAL DEFAULT 0.0
            );
            CREATE TABLE IF NOT EXISTS matches (
                id SERIAL PRIMARY KEY, 
                home_team TEXT, 
                away_team TEXT, 
                score_home INTEGER, 
                score_away INTEGER, 
                match_data JSONB
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("✅ База TONSCORE успешно запущена")
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")

init_db()

# --- ЛОГИКА ИИ (GEMINI) ---
SYSTEM_PROMPT = """
Ты — ИИ-Администратор футбольной лиги TONSCORE (FTCL 3). 
Твоя задача: анализировать отчеты о матчах и управлять базой данных.
Цветовая схема проекта: Красно-Алый.

Когда тебе присылают текст матча:
1. Выдели счет, авторов голов, ассистов.
2. Выдели лучших игроков и их оценки (дели на 10, например 84 -> 8.4).
3. Сформируй красивый отчет для админа.
4. В конце спроси: "Данные проверены? Вносим в базу?"
"""

@dp.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="TonScore", web_app=WebAppInfo(url=URL_SITE))]
    ])
    await message.answer(
        "<b>TonScore</b> доступен уже в этом мини приложении.\n\n"
        "Жми кнопку ниже, чтобы открыть панель управления лигой.",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.message(F.from_user.id == ADMIN_ID)
async def handle_admin_messages(message: Message):
    # Показываем, что бот думает
    await bot.send_chat_action(message.chat.id, "typing")
    
    try:
        # Отправляем запрос в Gemini
        chat = model.start_chat(history=[])
        response = chat.send_message(f"{SYSTEM_PROMPT}\n\nЗапрос от админа: {message.text}")
        
        await message.answer(f"🤖 <b>Ассистент TonScore:</b>\n\n{response.text}", parse_mode="HTML")
    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        await message.answer("⚠️ Ошибка связи с ИИ. Проверь GEMINI_API_KEY в настройках.")

# --- API ДЛЯ WEB APP (Чтобы приложение видело данные) ---
async def get_table(request):
    # В будущем здесь будет реальный SELECT из SQL
    data = {"teams": [
        {"name": "Ренти Сити", "points": 15},
        {"name": "Зёльден", "points": 12}
    ]}
    return web.json_response(data)

async def handle_index(request):
    with open("index.html", "r", encoding="utf-8") as f:
        return web.Response(text=f.read(), content_type='text/html')

# --- ЗАПУСК СЕРВЕРА И БОТА ---
app = web.Application()
app.router.add_get('/', handle_index)
app.router.add_get('/api/table', get_table)

async def main():
    # Запускаем бота
    asyncio.create_task(dp.start_polling(bot))
    
    # Запускаем веб-сервер для Web App
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    # Держим процесс запущенным
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
