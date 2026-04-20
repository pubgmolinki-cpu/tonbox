import os
import logging
import asyncio
import psycopg2
from groq import Groq
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# --- НАСТРОЙКИ ---
# Все ключи тянем из переменных Railway для безопасности
GROQ_KEY = os.environ.get("GROQ_API_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 1866813859
URL_SITE = os.environ.get("URL_SITE") 
DATABASE_URL = os.environ.get("DATABASE_URL")

logging.basicConfig(level=logging.INFO)

# Инициализация Groq (Проверь, что GROQ_API_KEY добавлен в Variables на Railway!)
client = Groq(api_key=GROQ_KEY)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
def init_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        # Создаем базовые таблицы, если их еще нет
        cur.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id SERIAL PRIMARY KEY, 
                name TEXT UNIQUE
            );
            CREATE TABLE IF NOT EXISTS players (
                id SERIAL PRIMARY KEY, 
                name TEXT, 
                goals INTEGER DEFAULT 0
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        logging.info("✅ База данных подключена и готова")
    except Exception as e:
        logging.error(f"❌ Ошибка БД: {e}")

# --- ОБРАБОТЧИКИ ТЕЛЕГРАМ ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    # Убеждаемся, что ссылка в кнопке корректная
    web_url = URL_SITE if URL_SITE.startswith("http") else f"https://{URL_SITE}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть TonScore 🏆", web_app=WebAppInfo(url=web_url))]
    ])
    await message.answer(
        "<b>Привет! Ты в панели управления TonScore.</b>\n\n"
        "Используй кнопку ниже, чтобы открыть приложение, или пиши мне вопросы как админ.",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.message(F.from_user.id == ADMIN_ID)
async def admin_ai_handler(message: Message):
    """Этот блок отвечает за работу ИИ-помощника"""
    await bot.send_chat_action(message.chat.id, "typing")
    try:
        # Используем актуальную модель llama-3.1
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Ты — помощник футбольной лиги TonScore. Отвечай кратко и профессионально."},
                {"role": "user", "content": message.text}
            ],
            model="llama-3.1-8b-instant",
        )
        response_text = chat_completion.choices[0].message.content
        await message.answer(f"🤖 {response_text}")
    except Exception as e:
        logging.error(f"Ошибка Groq: {e}")
        await message.answer(f"⚠️ Ошибка помощника: {str(e)}")

# --- ЛОГИКА ВЕБ-ПРИЛОЖЕНИЯ (WEB APP) ---

async def handle_index(request):
    """Отдает файл index.html из папки web"""
    # Путь к файлу: корень проекта / web / index.html
    path = os.path.join(os.getcwd(), "web", "index.html")
    
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return web.Response(text=content, content_type='text/html')
    else:
        # Если файла нет, выводим подсказку
        return web.Response(
            text="<h1>TonScore Live</h1><p>Ошибка: Создай папку <b>web</b> и положи туда <b>index.html</b></p>", 
            content_type='text/html', 
            status=404
        )

app = web.Application()
# Добавляем маршрут для главной страницы
app.router.add_get('/', handle_index)
# Если у тебя будут картинки или стили в web/static, бот их подтянет:
if os.path.exists("web/static"):
    app.router.add_static('/static/', path='web/static', name='static')

async def main():
    init_db()
    
    # Запускаем бота в фоновом режиме
    asyncio.create_task(dp.start_polling(bot))
    
    # Настраиваем и запускаем веб-сервер
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logging.info(f"🚀 Сервер запущен на порту {port}")
    
    # Бесконечный цикл, чтобы бот не выключался
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
