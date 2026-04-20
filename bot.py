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
GROQ_KEY = os.environ.get("GROQ_API_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 1866813859
URL_SITE = os.environ.get("URL_SITE") 
DATABASE_URL = os.environ.get("DATABASE_URL")

logging.basicConfig(level=logging.INFO)

# Инициализация Groq
client = Groq(api_key=GROQ_KEY)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ИНИЦИАЛИЗАЦИЯ БД ---
def init_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS teams (id SERIAL PRIMARY KEY, name TEXT UNIQUE);")
        conn.commit()
        cur.close()
        conn.close()
        logging.info("✅ База подключена")
    except Exception as e:
        logging.error(f"❌ Ошибка БД: {e}")

@dp.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть TonScore", web_app=WebAppInfo(url=URL_SITE))]
    ])
    await message.answer("<b>TonScore</b> запущен!", parse_mode="HTML", reply_markup=kb)

@dp.message(F.from_user.id == ADMIN_ID)
async def admin_ai_handler(message: Message):
    await bot.send_chat_action(message.chat.id, "typing")
    try:
        # Используем мощную модель Llama 3 через Groq
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": message.text}],
            model="llama-3.1-8b-instant",
        )
        await message.answer(f"🤖 {chat_completion.choices[0].message.content}")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)}")

# --- СЕРВЕР ---
async def handle_index(request):
    return web.Response(text="TonScore Live", content_type='text/html')

app = web.Application()
app.router.add_get('/', handle_index)

async def main():
    init_db()
    asyncio.create_task(dp.start_polling(bot))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    await site.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
