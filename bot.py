import os
import logging
import asyncio
import psycopg2
from groq import Groq
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# --- НАСТРОЙКИ (Берем из Environment Variables в Render) ---
GROQ_KEY = os.environ.get("GROQ_API_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 1866813859
# Важно: URL_SITE в Render должен быть без https:// в начале, скрипт добавит его сам
URL_SITE = os.environ.get("URL_SITE", "tonbox-1.onrender.com") 
DATABASE_URL = os.environ.get("DATABASE_URL")

logging.basicConfig(level=logging.INFO)

# Инициализация ИИ
client = Groq(api_key=GROQ_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
def init_db():
    if not DATABASE_URL:
        logging.error("❌ DATABASE_URL не найден в переменных окружения!")
        return
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS teams (id SERIAL PRIMARY KEY, name TEXT UNIQUE);
            CREATE TABLE IF NOT EXISTS players (id SERIAL PRIMARY KEY, name TEXT, goals INTEGER DEFAULT 0);
        """)
        conn.commit()
        cur.close()
        conn.close()
        logging.info("✅ База данных подключена и готова")
    except Exception as e:
        logging.error(f"❌ Ошибка БД: {e}")

# --- ОБРАБОТЧИКИ ТЕЛЕГРАМ ---

# ПРИОРИТЕТ 1: Команда /start (Всегда сверху!)
@dp.message(Command("start"))
async def cmd_start(message: Message):
    # Формируем ссылку правильно
    clean_url = URL_SITE.replace("https://", "").replace("http://", "")
    web_url = f"https://{clean_url}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть TonScore 🏆", web_app=WebAppInfo(url=web_url))]
    ])
    
    await message.answer(
        "<b>TonScore запущен!</b>\n\n"
        "Используй кнопку ниже для управления лигой или пиши вопросы помощнику.",
        parse_mode="HTML",
        reply_markup=kb
    )

# ПРИОРИТЕТ 2: Помощник для админа (Срабатывает только если это НЕ команда)
@dp.message(F.from_user.id == ADMIN_ID, F.text.exclude(Command))
async def admin_ai_handler(message: Message):
    await bot.send_chat_action(message.chat.id, "typing")
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Ты — помощник футбольной лиги TonScore. Отвечай кратко."},
                {"role": "user", "content": message.text}
            ],
            model="llama-3.1-8b-instant",
        )
        response_text = chat_completion.choices[0].message.content
        await message.answer(f"🤖 {response_text}")
    except Exception as e:
        logging.error(f"Ошибка Groq: {e}")
        await message.answer(f"⚠️ Ошибка помощника: {str(e)}")

# --- ЛОГИКА ВЕБ-СЕРВЕРА (Для Web App) ---

async def handle_index(request):
    path = os.path.join(os.getcwd(), "web", "index.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return web.Response(text=content, content_type='text/html')
    return web.Response(text="<h1>TonScore</h1><p>Файл index.html не найден в папке web</p>", content_type='text/html', status=404)

app = web.Application()
app.router.add_get('/', handle_index)
if os.path.exists("web/static"):
    app.router.add_static('/static/', path='web/static', name='static')

async def main():
    init_db()
    # Запуск бота
    asyncio.create_task(dp.start_polling(bot))
    # Запуск сервера на порту Render
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logging.info(f"🚀 Бот и сервер запущены на порту {port}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Остановлено")
