import os
import logging
import asyncio
import psycopg2
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# --- НАСТРОЙКИ ---
# Берем данные из секретных переменных Railway
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 1866813859
URL_SITE = os.environ.get("URL_SITE") 
DATABASE_URL = os.environ.get("DATABASE_URL")

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# --- ИНИЦИАЛИЗАЦИЯ GEMINI ---
if not GEMINI_KEY:
    logging.error("❌ Переменная GEMINI_API_KEY не задана!")
else:
    # transport='rest' решает проблему с gRPC на некоторых серверах
    genai.configure(api_key=GEMINI_KEY, transport='rest')

# Создаем модель с явными настройками, чтобы избежать 404
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config={
        "temperature": 0.7,
        "top_p": 0.95,
        "max_output_tokens": 1024,
    }
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
def init_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
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
        logging.info("✅ База данных подключена")
    except Exception as e:
        logging.error(f"❌ Ошибка БД: {e}")

# --- ОБРАБОТЧИКИ КОМАНД ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть TonScore", web_app=WebAppInfo(url=URL_SITE))]
    ])
    await message.answer(
        "<b>TonScore</b> готов к работе.\n\nИспользуй кнопку ниже для управления лигой.",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.message(F.from_user.id == ADMIN_ID)
async def admin_ai_handler(message: Message):
    await bot.send_chat_action(message.chat.id, "typing")
    try:
        # Запрос к Gemini
        response = model.generate_content(f"Ты помощник футбольной лиги. Коротко ответь на вопрос: {message.text}")
        await message.answer(f"🤖 {response.text}")
        
    except Exception as e:
        logging.error(f"Ошибка ИИ: {e}")
        # Выводим понятную ошибку в чат для отладки
        error_msg = str(e)
        if "404" in error_msg:
            await message.answer("⚠️ Ошибка 404: Модель не найдена. Проверь, что API ключ активен в Google AI Studio.")
        elif "API_KEY_INVALID" in error_msg:
            await message.answer("⚠️ Ошибка: API ключ недействителен. Обнови его в Variables на Railway.")
        else:
            await message.answer(f"⚠️ Произошла ошибка: {error_msg}")

# --- ВЕБ-СЕРВЕР ДЛЯ WEB APP ---
async def handle_index(request):
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type='text/html')
    except FileNotFoundError:
        return web.Response(text="index.html не найден", status=404)

app = web.Application()
app.router.add_get('/', handle_index)

async def main():
    init_db()
    
    # Запускаем бота
    asyncio.create_task(dp.start_polling(bot))
    
    # Запускаем сервер на порту Railway
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот выключен")
