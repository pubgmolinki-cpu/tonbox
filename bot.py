import os
import logging
import asyncio
import psycopg2
import json
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
    """Универсальная функция для запросов к БД"""
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
        logging.error(f"Ошибка БД: {e}")
        return None

def add_goal_to_player(player_name, goals=1):
    """Записывает голы игроку"""
    # Проверяем, есть ли игрок, если нет — создаем
    exists = db_execute("SELECT id FROM players WHERE name = %s", (player_name,), fetch=True)
    if exists:
        db_execute("UPDATE players SET goals = goals + %s WHERE name = %s", (goals, player_name))
    else:
        db_execute("INSERT INTO INTO players (name, goals) VALUES (%s, %s)", (player_name, goals))
    return f"✅ Записано: {player_name} +{goals} гол(а)."

def get_stats():
    """Получает топ бомбардиров"""
    rows = db_execute("SELECT name, goals FROM players ORDER BY goals DESC LIMIT 5", fetch=True)
    if not rows: return "Статистика пока пуста."
    return "\n".join([f"⚽ {r[0]}: {r[1]}" for r in rows])

# --- ЛОГИКА ИИ С ИНСТРУМЕНТАМИ ---

async def ask_ai_with_tools(user_text):
    """ИИ анализирует текст и решает, нужно ли обновить БД"""
    prompt = f"""
    Ты — менеджер TonScore. Твоя задача: помогать админу управлять статистикой.
    Если админ говорит записать гол (например 'Месси забил 2'), отвечай строго в формате:
    [ACTION:ADD_GOAL, PLAYER:имя, COUNT:число]
    Если админ просит таблицу или статс:
    [ACTION:GET_STATS]
    В остальных случаях просто отвечай на вопрос.
    Текст админа: {user_text}
    """
    
    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.1-8b-instant",
    )
    ai_response = completion.choices[0].message.content

    # Обработка команд от ИИ
    if "[ACTION:ADD_GOAL" in ai_response:
        # Парсим имя и количество (упрощенно)
        try:
            name = ai_response.split("PLAYER:")[1].split(",")[0].strip()
            count = int(ai_response.split("COUNT:")[1].split("]")[0].strip())
            result = add_goal_to_player(name, count)
            return result
        except:
            return "❌ Не удалось распознать данные для записи."
    
    elif "[ACTION:GET_STATS]" in ai_response:
        return f"📊 Текущая статистика:\n{get_stats()}"
    
    return ai_response

# --- ОБРАБОТЧИКИ ТЕЛЕГРАМ ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    clean_url = URL_SITE.replace("https://", "").replace("http://", "").strip("/")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть TonScore 🏆", web_app=WebAppInfo(url=f"https://{clean_url}"))]
    ])
    await message.answer("<b>TonScore готов!</b>\nПиши статистику (например: 'Роналду забил 1') или задавай вопросы.", parse_mode="HTML", reply_markup=kb)

@dp.message(F.from_user.id == ADMIN_ID)
async def admin_ai_handler(message: Message):
    if message.text and message.text.startswith("/"): return
    
    await bot.send_chat_action(message.chat.id, "typing")
    answer = await ask_ai_with_tools(message.text)
    await message.answer(answer)

# --- СЕРВЕР ---
async def handle_index(request):
    path = os.path.join(os.getcwd(), "web", "index.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type='text/html')
    return web.Response(text="TonScore Live")

app = web.Application()
app.router.add_get('/', handle_index)

async def main():
    # Инициализация таблиц
    db_execute("CREATE TABLE IF NOT EXISTS players (id SERIAL PRIMARY KEY, name TEXT, goals INTEGER DEFAULT 0)")
    
    asyncio.create_task(dp.start_polling(bot))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
