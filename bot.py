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

# Инициализация ИИ и Бота
client = Groq(api_key=GROQ_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ФУНКЦИИ БАЗЫ ДАННЫХ ---
def db_execute(query, params=(), fetch=False):
    if not DATABASE_URL:
        logging.error("❌ DATABASE_URL не найден!")
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

# --- API ДЛЯ WEB APP (Чтобы сайт видел данные) ---
async def get_stats_api(request):
    rows = db_execute("SELECT name, goals FROM players ORDER BY goals DESC", fetch=True)
    stats = [{"name": r[0], "goals": r[1]} for r in rows] if rows else []
    return web.json_response(stats)

async def handle_index(request):
    path = os.path.join(os.getcwd(), "web", "index.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type='text/html')
    return web.Response(text="<h1>TonScore Live</h1><p>Файл index.html не найден.</p>", content_type='text/html', status=404)

# --- ЛОГИКА ИИ-ПОМОЩНИКА ---
async def ask_ai_with_tools(user_text):
    prompt = f"""
    Ты — технический модуль управления статистикой TonScore.
    Если админ просит записать гол, ответь СТРОГО в формате:
    [ACTION:ADD_GOAL, PLAYER:имя, COUNT:число]
    Пример: "Месси забил 2" -> [ACTION:ADD_GOAL, PLAYER:Месси, COUNT:2]
    Если это просто вопрос, отвечай как обычно.
    Текст: {user_text}
    """
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        ai_res = completion.choices[0].message.content
        
        if "[ACTION:ADD_GOAL" in ai_res:
            name = ai_res.split("PLAYER:")[1].split(",")[0].strip()
            count = int(ai_res.split("COUNT:")[1].split("]")[0].strip())
            
            db_execute("""
                INSERT INTO players (name, goals) 
                VALUES (%s, %s) 
                ON CONFLICT (name) 
                DO UPDATE SET goals = players.goals + EXCLUDED.goals
            """, (name, count))
            return f"✅ Статистика обновлена: <b>{name}</b> +{count} гол(а)."
        
        return ai_res
    except Exception as e:
        return f"⚠️ Ошибка обработки: {str(e)}"

# --- ОБРАБОТЧИКИ ТЕЛЕГРАМ ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    clean_url = URL_SITE.replace("https://", "").replace("http://", "").strip("/")
    web_url = f"https://{clean_url}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть TonScore 🏆", web_app=WebAppInfo(url=web_url))]
    ])
    await message.answer("<b>🏆 ТонСкоре готов!</b>\nПиши статистику (н-р: 'Лео 1'), я внесу её в базу.", parse_mode="HTML", reply_markup=kb)

@dp.message(F.from_user.id == ADMIN_ID)
async def admin_handler(message: Message):
    if message.text and not message.text.startswith("/"):
        await bot.send_chat_action(message.chat.id, "typing")
        ans = await ask_ai_with_tools(message.text)
        await message.answer(ans, parse_mode="HTML")

# --- СЕРВЕР И ЗАПУСК ---
app = web.Application()
app.router.add_get('/', handle_index)
app.router.add_get('/api/stats', get_stats_api)
if os.path.exists("web/static"):
    app.router.add_static('/static/', path='web/static', name='static')

async def main():
    # Создаем таблицу
    db_execute("CREATE TABLE IF NOT EXISTS players (id SERIAL PRIMARY KEY, name TEXT UNIQUE, goals INTEGER DEFAULT 0)")
    
    asyncio.create_task(dp.start_polling(bot))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    logging.info(f"🚀 Запущено на порту {port}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
