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

# Определяем базовую директорию проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "news.json")
STATIC_DIR = os.path.join(BASE_DIR, "static")

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

class NewPost(StatesGroup):
    photo = State()
    title = State()
    content = State()

# --- ЛОГИКА БОТА ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Читать TONBOX NEWS ⚽️", web_app=WebAppInfo(url=URL_SITE))]
    ])
    await message.answer(f"Привет, {message.from_user.first_name}!\nДобро пожаловать в TONBOX NEWS.", reply_markup=kb)

@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: Message, state: FSMContext):
    await message.answer("🛠 **Админка**\nПришли ФОТОГРАФИЮ для новости:")
    await state.set_state(NewPost.photo)

@dp.message(NewPost.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_name = f"{uuid.uuid4()}.jpg"
    file_path = os.path.join(STATIC_DIR, file_name)
    await bot.download_file(file_info.file_path, file_path)
    await state.update_data(photo_url=f"/static/{file_name}")
    await message.answer("Введите ЗАГОЛОВОК новости:")
    await state.set_state(NewPost.title)

@dp.message(NewPost.title)
async def set_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите ТЕКСТ новости:")
    await state.set_state(NewPost.content)

@dp.message(NewPost.content)
async def save_new_post(message: Message, state: FSMContext):
    data = await state.get_data()
    news_list.insert(0, {
        "image_url": data['photo_url'],
        "title": data['title'],
        "content": message.text
    })
    save_news_to_file()
    await message.answer("✅ Новость опубликована!")
    await state.clear()

@dp.message(Command("manage"), F.from_user.id == ADMIN_ID)
async def manage_news(message: Message):
    if not news_list:
        await message.answer("Новостей нет.")
        return
    for index, news in enumerate(news_list):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="❌ Удалить", callback_data=f"del_{index}"))
        await message.answer(f"🔹 {news['title']}", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("del_"))
async def delete_callback(callback: types.CallbackQuery):
    idx = int(callback.data.split("_")[1])
    try:
        removed = news_list.pop(idx)
        save_news_to_file()
        await callback.message.edit_text(f"🗑 Удалено: {removed['title']}")
    except:
        await callback.answer("Ошибка")

# --- УЛУЧШЕННЫЙ ВЕБ-СЕРВЕР ---

async def handle_api(request):
    return web.json_response(news_list)

async def handle_site(request):
    # Пытаемся найти index.html в корне проекта
    path_to_html = os.path.join(BASE_DIR, 'index.html')
    
    if os.path.exists(path_to_html):
        with open(path_to_html, 'r', encoding='utf-8') as f:
            return web.Response(text=f.read(), content_type='text/html')
    else:
        return web.Response(text=f"Ошибка: index.html не найден. Проверь корень проекта. Путь на сервере: {path_to_html}", status=404)

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
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
