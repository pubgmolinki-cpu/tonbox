import os
import logging
import asyncio
import psycopg2
from groq import Groq
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# --- НАСТРОЙКИ (Variables из Render) ---
GROQ_KEY = os.environ.get("GROQ_API_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 1866813859
URL_SITE = os.environ.get("URL_SITE", "tonbox-1.onrender.com") 
DATABASE_URL = os.environ.get("DATABASE_URL")

logging.basicConfig(level=logging.INFO)

# Инициализация ИИ
client = Groq(api_key=GROQ_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    if not DATABASE_URL:
        logging.error("❌ DATABASE_URL не найден")
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
        logging.info("✅ База подключена")
    except Exception as e:
        logging.error(f"❌ Ошибка БД: {e}")

# --- ОБРАБОТЧИКИ ТЕЛЕГРАМ ---

# 1. СТРОГИЙ ПРИОРИТЕТ: Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    # Чистим URL от лишних знаков
    clean_url = URL_SITE.replace("https://", "").replace("http://", "").strip("/")
    web_url = f"https://{clean_url}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть TonScore 🏆", web_app=WebAppInfo(url=web_url))]
    ])
    
    await message.answer(
        "<b>TonScore готов к работе.</b>\n\nИспользуй кнопку ниже для управления лигой.",
        parse_mode="HTML",
        reply_markup=kb
    )

# 2. ПРИОРИТЕТ 2: Все остальное от админа уходит ИИ
@dp.message(F.from_user.id == ADMIN_ID)
async def admin_ai_handler(message: Message):
    # Если это любая другая команда (начинается с /), которую мы не описали — игнорим
    if message.text and message.text.startswith("/"):
        return

    # Если это обычный текст — отвечает ИИ
    await bot.send_chat_action(message.chat.id, "typing")
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Ты — помощник футбольной лиги TonScore. Отвечай кратко."},
                {"role": "user", "content": message.text}
            ],
            model="llama-3.1-8b-instant", # Актуальная модель
        )
        response_text = chat_completion.choices[0].message.content
        await message.answer(f"🤖 {response_text}")
    except Exception as e:
        logging.error(f"Ошибка Groq: {e}")
        await message.answer(f"⚠️ Ошибка помощника: {str(e)}")

# --- ВЕБ-СЕРВЕР (Для работы Web App) ---

async def handle_index(request):
    path = os.path.join(os.getcwd(), "web", "index.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return web.Response(text=content, content_type='text/html')
    return web.Response(text="TonScore Live", content_type='text/html')

app = web.Application()
app.router.add_get('/', handle_index)

# Поддержка статики (стили, картинки), если они есть в папке web/static
if os.path.exists("web/static"):
    app.router.add_static('/static/', path='web/static', name='static')

async def main():
    init_db()
    # Фоновый запуск бота
    asyncio.create_task(dp.start_polling(bot))
    # Запуск сервера на порту Render
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logging.info(f"🚀 Сервер запущен на порту {port}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Остановлено")
