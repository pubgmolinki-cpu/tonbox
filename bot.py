import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

# --- НАСТРОЙКИ ---
# Вставь свои данные здесь, если не используешь переменные окружения Railway
TOKEN = "8617831885:AAGuiDHofe7tvx0QwS8xJfcNhO-TkfCduOA"
ADMIN_ID = 1866813859  # Твой цифровой ID (числом)
URL_SITE = "https://o964180m.beget.tech/" # Адрес твоего сайта на Beget
SECRET_KEY = "МОЙ_СЕКРЕТНЫЙ_КЛЮЧ" # Должен совпадать с ключом в post_news.php

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Состояния для пошагового создания новости
class NewPost(StatesGroup):
    photo_url = State()
    title = State()
    content = State()

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Читать новости ⚽️", web_app=WebAppInfo(url=URL_SITE))]
    ])
    await message.answer(
        f"Привет, {message.from_user.first_name}!\n\n"
        "Добро пожаловать в официальный бот лиги FTCL 3. "
        "Нажимай на кнопку ниже, чтобы открыть наш стильный сайт с новостями!",
        reply_markup=kb
    )

# Вход в админку
@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: Message, state: FSMContext):
    await message.answer("🛠 **Админ-панель**\n\nОтправь прямую ССЫЛКУ на фото новости:")
    await state.set_state(NewPost.photo_url)

# Состояние: Получение ссылки на фото
@dp.message(NewPost.photo_url)
async def set_photo(message: Message, state: FSMContext):
    if not message.text.startswith("http"):
        await message.answer("Пожалуйста, отправь корректную ссылку (начинается с http...)")
        return
    await state.update_data(photo_url=message.text)
    await message.answer("Теперь введи ЗАГОЛОВОК новости:")
    await state.set_state(NewPost.title)

# Состояние: Получение заголовка
@dp.message(NewPost.title)
async def set_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите основной ТЕКСТ новости:")
    await state.set_state(NewPost.content)

# Состояние: Получение текста и отправка на Beget
@dp.message(NewPost.content)
async def save_news(message: Message, state: FSMContext):
    data = await state.get_data()
    post_data = {
        'image': data['photo_url'],
        'title': data['title'],
        'content': message.text
    }
    
    # URL твоего PHP-обработчика на Beget
    api_url = f"{URL_SITE}/post_news.php?key={SECRET_KEY}"
    
    await message.answer("📤 Публикация... подожди секунду.")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, data=post_data) as response:
                result = await response.text()
                if response.status == 200 and "Success" in result:
                    await message.answer("✅ Новость успешно опубликована на сайте!")
                else:
                    await message.answer(f"❌ Ошибка сервера Beget: {result}")
    except Exception as e:
        await message.answer(f"❌ Не удалось связаться с сайтом: {e}")
    
    await state.clear()

# Запуск бота
async def main():
    print("Бот FTCL 3 запущен на Railway!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
