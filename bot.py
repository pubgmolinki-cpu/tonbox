import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo
from aiohttp import web

# Конфигурация
API_TOKEN = '8714249606:AAFZrZfOeCw0PX-93Gfac3wPfXbRx7JDGD8'
WEBAPP_URL = 'https://tonbox-1.onrender.com' # Ссылка после деплоя

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Обработка команды /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    markup = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(
                text="Открыть Fantasy FTCL",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )]
        ],
        resize_keyboard=True
    )
    await message.answer("Добро пожаловать в Fantasy FTCL! Жми кнопку ниже, чтобы собрать состав.", reply_markup=markup)

# Прием данных от Web App (когда юзер нажал "Сохранить")
@dp.message(F.content_type == types.ContentType.WEB_APP_DATA)
async def web_app_data_handler(message: types.Message):
    data = message.web_app_data.data
    await message.answer(f"Состав принят! Твой бюджет: {data} монет. Удачи в туре!")

# Настройка aiohttp для отдачи HTML страницы
async def handle_index(request):
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        return web.Response(text=f.read(), content_type='text/html')

async def main():
    # Создаем aiohttp приложение для Web App
    app = web.Application()
    app.router.add_get('/', handle_index)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    
    # Запускаем бота и веб-сервер параллельно
    await asyncio.gather(
        site.start(),
        dp.start_polling(bot)
    )

if __name__ == '__main__':
    asyncio.run(main())
