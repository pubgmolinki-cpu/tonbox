import asyncio
import os
import logging
import json
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8613728108:AAGR9Lmdx2YvG6wbg8qk31rcLxeKD4Vu6Po"
ADMIN_ID = 1866813859 
URL_SITE = "https://tonbox-news.onrender.com" 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DB_FILE = "news.json"
STATIC_DIR = "static"

if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

def load_news():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []

def save_news_to_file():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=4)

news_list = load_news()

# --- HTML КОД (Прямо в переменной) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TONBOX NEWS</title>
    <style>
        body { background: #0a0a0c; color: #fff; font-family: sans-serif; padding: 15px; margin: 0; }
        h1 { color: #ff004c; text-align: center; font-size: 24px; }
        .card { background: #161618; border-radius: 15px; margin-bottom: 20px; overflow: hidden; border: 1px solid #222; }
        .card img { width: 100%; height: 200px; object-fit: cover; }
        .card-body { padding: 15px; }
        h2 { margin: 0 0 10px; font-size: 18px; color: #ff004c; }
        p { font-size: 14px; opacity: 0.8; line-height: 1.4; }
    </style>
</head>
<body>
    <h1>TONBOX NEWS ⚽️</h1>
    <div id="news"></div>
    <script>
        async function load() {
            const r = await fetch('/api/news');
            const data = await r.json();
            const cont = document.getElementById('news');
            if (data.length === 0) { cont.innerHTML = '<p style="text-align:center">Новостей пока нет...</p>'; return; }
            cont.innerHTML = data.map(n => `
                <div class="card">
                    <img src="${n.image_url}" onerror="this.src='https://via.placeholder.com/400x200?text=News'">
                    <div class="card-body">
                        <h2>${n.title}</h2>
                        <p>${n.content}</p>
                    </div>
                </div>
            `).join('');
        }
        load();
    </script>
</body>
</html>
"""

class NewPost(StatesGroup):
    photo = State()
    title = State()
    content = State()

# --- БОТ ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть TONBOX NEWS", web_app=WebAppInfo(url=URL_SITE))]
    ])
    await message.answer("Добро пожаловать в TONBOX NEWS!", reply_markup=kb)

@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: Message, state: FSMContext):
    await message.answer("Пришли ФОТО:")
    await state.set_state(NewPost.photo)

@dp.message(NewPost.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_name = f"{uuid.uuid4()}.jpg"
    file_path = os.path.join(STATIC_DIR, file_name)
    await bot.download_file(file_info.file_path, file_path)
    await state.update_data(photo_url=f"/static/{file_name}")
    await message.answer("Заголовок:")
    await state.set_state(NewPost.title)

@dp.message(NewPost.title)
async def set_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Текст:")
    await state.set_state(NewPost.content)

@dp.message(NewPost.content)
async def save_new_post(message: Message, state: FSMContext):
    data = await state.get_data()
    news_list.insert(0, {"image_url": data['photo_url'], "title": data['title'], "content": message.text})
    save_news_to_file()
    await message.answer("✅ Опубликовано!")
    await state.clear()

# --- СЕРВЕР ---
async def handle_api(request):
    return web.json_response(news_list)

async def handle_site(request):
    return web.Response(text=HTML_TEMPLATE, content_type='text/html')

app = web.Application()
app.router.add_get('/', handle_site)
app.router.add_get('/api/news', handle_api)
app.router.add_static('/static/', path=STATIC_DIR, name='static')

async def main():
    asyncio.create_task(dp.start_polling(bot))
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', port).start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
