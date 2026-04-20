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
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 1866813859
URL_SITE = os.environ.get("URL_SITE") 
DATABASE_URL = os.environ.get("DATABASE_URL")

logging.basicConfig(level=logging.INFO)

# --- ИНИЦИАЛИЗАЦИЯ GEMINI (FIXED) ---
if not GEMINI_KEY:
    logging.error("❌ GEMINI_API_KEY не найден в Variables!")
else:
    # Отключаем использование mTLS и принудительно ставим REST для стабильности на Railway
    os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"
    genai.configure(api_key=GEMINI_KEY, transport='rest')

# Создаем модель через стабильный путь
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

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
                goals INTEGER DEFAULT 0, 
                assists INTEGER DEFAULT 0, 
                rating REAL DEFAULT 0.0
            );
            CREATE TABLE IF NOT EXISTS matches (
                id SERIAL PRIMARY KEY, 
                home_team TEXT, 
                away_team TEXT, 
                score_home INTEGER, 
                score_away INTEGER
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        logging.info("✅ База TONSCORE успешно подключена")
    except Exception as e:
        logging.error(f"❌ Ошибка БД: {e}")

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    # Проверка на наличие https:// в URL
    web_url = URL_SITE if URL_SITE.startswith("http") else f"https://{URL_SITE}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть TonScore", web_app=WebAppInfo(url=web_url))]
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
        # Прямой вызов генерации контента
        response = model.generate_content(f"Ты ассистент лиги TonScore. Ответь кратко: {message.text}")
        
        if response and response.text:
            await message.answer(f"🤖 {response.text}")
        else:
            await message.answer("🤖 ИИ не смог сформировать ответ. Попробуй еще раз.")
            
    except Exception as e:
        logging.error(f"Ошибка Gemini: {e}")
        err_msg = str(e)
        if "404" in err_msg:
            await message.answer("⚠️ Ошибка 404: Модель всё еще не видна. Попробуй создать ключ в новом проекте Google AI Studio.")
        else:
            await message.answer(f"⚠️ Ошибка ИИ: {err_msg}")

# --- СЕРВЕР ДЛЯ WEB APP ---
async def handle_index(request):
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type='text/html')
    except Exception:
        return web.Response(text="index.html не найден", status=404)

app = web.Application()
app.router.add_get('/', handle_index)

async def main():
    init_db()
    asyncio.create_task(dp.start_polling(bot))
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
