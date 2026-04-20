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
URL_SITE = os.environ.get("URL_SITE", "tonbox-1.onrender.com") 
DATABASE_URL = os.environ.get("DATABASE_URL")

logging.basicConfig(level=logging.INFO)

client = Groq(api_key=GROQ_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ФУНКЦИИ БАЗЫ ДАННЫХ ---
def db_execute(query, params=(), fetch=False):
    if not DATABASE_URL:
        logging.error("❌ DATABASE_URL отсутствует в переменных!")
        return None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(query, params)
        res = cur.fetchall() if fetch else None
        conn.commit()
        cur.close()
        conn.close()
        return res
    except Exception as e:
        logging.error(f"❌ Ошибка БД: {e}")
        return None

# --- API ДЛЯ САЙТА ---
async def get_stats_api(request):
    rows = db_execute("SELECT name, goals FROM players ORDER BY goals DESC", fetch=True)
    stats = [{"name": r[0], "goals": r[1]} for r in rows] if rows else []
    return web.json_response(stats)

async def handle_index(request):
    path = os.path.join(os.getcwd(), "web", "index.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type='text/html')
    return web.Response(text="index.html не найден", status=404)

# --- ЛОГИКА ИИ С ОТЛАДКОЙ ---
async def ask_ai_and_record(message: Message):
    user_text = message.text
    prompt = f"""
    Ты — системный модуль записи статистики TonScore.
    Если админ пишет кто забил голы, ты ОБЯЗАТЕЛЬНО должен вернуть команду в формате:
    [ACTION:ADD_GOAL, PLAYER:имя, COUNT:число]
    Пример: "Месси 2" -> [ACTION:ADD_GOAL, PLAYER:Месси, COUNT:2]
    Если это просто вопрос, отвечай как обычно.
    Текст: {user_text}
    """
    
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        ai_res = completion.choices[0].message.content
        
        # ЛОГ ДЛЯ ТЕБЯ (Удалим потом)
        logging.info(f"ИИ ответил: {ai_res}")

        if "[ACTION:ADD_GOAL" in ai_res:
            name = ai_res.split("PLAYER:")[1].split(",")[0].strip()
            count = int(ai_res.split("COUNT:")[1].split("]")[0].strip())
            
            db_execute("""
                INSERT INTO players (name, goals) 
                VALUES (%s, %s) 
                ON CONFLICT (name) 
                DO UPDATE SET goals = players.goals + EXCLUDED.goals
            """, (name, count))
            
            await message.answer(f"✅ <b>Записано в базу:</b> {name} +{count}")
        else:
            # Если ИИ просто ответил текстом
            await message.answer(f"🤖 {ai_res}")
            
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)}")

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    clean_url = URL_SITE.replace("https://", "").replace("http://", "").strip("/")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть TonScore 🏆", web_app=WebAppInfo(url=f"https://{clean_url}"))]
    ])
    await message.answer("<b>🏆 ТонСкоре Админ</b>\nПиши статистику (например: 'Муньез 2')", parse_mode="HTML", reply_markup=kb)

@dp.message(F.from_user.id == ADMIN_ID)
async def admin_handler(message: Message):
    if message.text and not message.text.startswith("/"):
        await bot.send_chat_action(message.chat.id, "typing")
        await ask_ai_and_record(message)

# --- ЗАПУСК ---
app = web.Application()
app.router.add_get('/', handle_index)
app.router.add_get('/api/stats', get_stats_api)

async def main():
    # Проверка и создание таблицы при запуске
    db_execute("CREATE TABLE IF NOT EXISTS players (id SERIAL PRIMARY KEY, name TEXT UNIQUE, goals INTEGER DEFAULT 0)")
    
    asyncio.create_task(dp.start_polling(bot))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    logging.info(f"🚀 Сервер на порту {port}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
