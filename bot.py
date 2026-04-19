import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
import jinja2
import aiohttp_jinja2

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8617831885:AAGuiDHofe7tvx0QwS8xJfcNhO-TkfCduOA"
ADMIN_ID = 1866813859  # Твой ID
# Render сам подставит URL, но для кнопки в боте укажи свой адрес после деплоя
URL_SITE = "https://tonbox-araq.onrender.com" 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Список для хранения новостей (в идеале использовать БД, но для начала хватит списка)
news_list = [
    {
        "image_url": "https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=800",
        "title": "Добро пожаловать в FTCL 3",
        "content": "Это первая новость. Здесь будут публиковаться все важные события лиги!"
    }
]

# --- СОСТОЯНИЯ АДМИНКИ ---
class NewPost(StatesGroup):
    photo_url = State()
    title = State()
    content = State()

# --- ЛОГИКА БОТА ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Читать новости ⚽️", web_app=WebAppInfo(url=URL_SITE))]
    ])
    await message.answer("Привет! Следи за новостями FTCL 3 прямо здесь.", reply_markup=kb)

@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: Message, state: FSMContext):
    await message.answer("🛠 Админка: Отправь ССЫЛКУ на фото:")
    await state.set_state(NewPost.photo_url)

@dp.message(NewPost.photo_url)
async def set_photo(message: Message, state: FSMContext):
    await state.update_data(photo_url=message.text)
    await message.answer("Введи ЗАГОЛОВОК:")
    await state.set_state(NewPost.title)

@dp.message(NewPost.title)
async def set_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введи ТЕКСТ новости:")
    await state.set_state(NewPost.content)

@dp.message(NewPost.content)
async def save_news(message: Message, state: FSMContext):
    data = await state.get_data()
    news_list.insert(0, {
        "image_url": data['photo_url'],
        "title": data['title'],
        "content": message.text
    })
    await message.answer("✅ Новость добавлена!")
    await state.clear()

# --- ЛОГИКА ВЕБ-СЕРВЕРА (САЙТА) ---
async def handle_index(request):
    # Этот эндпоинт отдает JSON с новостями для нашего сайта
    return web.json_response(news_list)

async def handle_site(request):
    # Читаем index.html и отдаем его пользователю
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    return web.Response(text=html, content_type='text/html')

app = web.Application()
app.router.add_get('/', handle_site)       # Отдает сам сайт
app.router.add_get('/api/news', handle_index) # Отдает данные новостей

# --- ЗАПУСК ---
async def main():
    # Запуск бота в фоне
    asyncio.create_task(dp.start_polling(bot))
    
    # Запуск веб-сервера
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logging.info(f"Сайт и Бот запущены на порту {port}")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
