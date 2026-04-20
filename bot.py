import os
import logging
import asyncio
import psycopg2
import json
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# --- НАСТРОЙКИ ---
# Теперь ключ берется из Variables Railway автоматически
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 1866813859
URL_SITE = os.environ.get("URL_SITE") 
DATABASE_URL = os.environ.get("DATABASE_URL")

# Проверка наличия ключа перед запуском
if not GEMINI_KEY:
    logging.error("❌ GEMINI_API_KEY не найден в переменных окружения!")
else:
    genai.configure(api_key=GEMINI_KEY)

model = genai.GenerativeModel('models/gemini-1.5-flash')

logging.basicConfig(level=logging.INFO)
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
                team_id INTEGER, 
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

# --- ЛОГИКА ИИ ПОМОЩНИКА ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    # Убедись, что URL_SITE в Railway начинается с https://
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
async def admin_ai(message: Message):
    await bot.send_chat_action(message.chat.id, "typing")
    try:
        # Промпт для ИИ, чтобы он понимал контекст
        prompt = f"""
        Ты — ИИ-ассистент футбольной лиги TONSCORE. 
        Помогай администратору управлять игроками и матчами.
        Отвечай кратко и по делу.
        
        Запрос админа: {message.text}
        """
        
        response = model.generate_content(prompt)
        await message.answer(f"🤖 {response.text}")
        
    except Exception as e:
        logging.error(f"Ошибка Gemini: {e}")
        await message.answer(f"⚠️ Ошибка ИИ: Скорее всего, ключ в Variables еще не обновился или не верен.\n\nДетали: {str(e)}")

# --- СЕРВЕР ДЛЯ WEB APP ---
async def handle_index(request):
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type='text/html')
    except FileNotFoundError:
        return web.Response(text="Файл index.html не найден!", status=404)

app = web.Application()
app.router.add_get('/', handle_index)

async def main():
    init_db()
    # Запуск бота и сервера параллельно
    asyncio.create_task(dp.start_polling(bot))
    
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
        logging.info("Бот остановлен")
