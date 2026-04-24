import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from openai import AsyncOpenAI
from aiohttp import web

# ================= КОНФИГУРАЦИЯ (ENV) =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LOG_GROUP_ID = int(os.getenv("LOG_GROUP_ID", "0"))

client = AsyncOpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# ================= ВЕБ-СЕРВЕР ДЛЯ RENDER =================
async def handle(request):
    return web.Response(text="Симуляция активна. Бот работает.")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# ================= КЛАВИАТУРЫ =================
def done_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="✅ Готово (Конец текста)")
    return builder.as_markup(resize_keyboard=True)

def main_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="Симуляция Матча")
    builder.button(text="Чистка Тактик")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# ================= ПОЛНЫЕ ШАБЛОНЫ =================

CLEAN_TACTIC_TEMPLATE = """Бот, проанализируй и отредактируй эту тактику.

Исключи из неё:
 * Любые нереалистичные действия и отсылки к истории подготовки или конкретному сопернику.
 * Психологические оценки, высокую боевую готовность и абстрактные понятия (дух, характер, интуиция, химия).
 * Глаголы неуверенности и попытки (стараться, пытаться, стремиться, пробовать) — заменяй их на конкретные действия.
 * Любые метафоры, журналистские штампы и идиомы.
 * Субъективные оценочные прилагательные (опасный, уверенный, рискованный, грамотный).
 * Слова 'цель', 'стратегия', 'задача' и эпитеты.

Если какие-то принципы изложены избыточно, сделай формулировки сухими, императивными и технически точными. Используй терминологию (полуфланг, зона 14, низкий блок и т.д.), не меняя при этом структуру модели. Отправь мне финальный текст.

Если этого всего нет, просто скажи, что тактика чистая и не подлежит чистке.

Вот сама тактика:
{user_tactic}"""

SIMULATION_FULL_TEMPLATE = """Бот, просимулируй этот матч:
Матч: {home_name} (Дома) vs {away_name} (Гости)

1. Факторы симуляции:
• Тактика (65%): Главный элемент. Определяет рисунок игры.
• Рейтинг игроков (30%): Класс исполнителей.
• Судья (3%): Выбираешь сам. Строгость влияет на карточки, штрафные, пенальти.
• Погода (1%): Выбираешь сам, исходя из места проведения матча. Влияет на ошибки и физику.
• Удача (1%): Случайные отскоки, везение.
• Домашний фактор: Дает только + к мотивации (не к скиллам).
• Место проведения матча: {stadium}

2. Система рейтингов (Уровень)
 * 95: Обладатель «Золотого Мяча»
 * 90: Мировой класс, лидер.
 * 85: Звезда.
 * 80: Хороший игрок основы.
 * 75: Середняк.
 * 70: Профессионал (ниже среднего).
 * 65: Продвинутый полупрофи (Недотягивает до профессионала)
 * 60: Полупрофи.
 * 55: Продвинутый новичок (недотягивает до полупрофи)
 * 50: Новичок.
 * 00: Игрока фактически не было на поле, худший рейтинг.
 * Примечание: Команды с игроками 90+ атакуют чаще. Чем слабее вратари/защитники — больше шанс на пропущенный гол.
 * Пиши также тип травмы/повреждения:
 • Легкая: Ушиб (может доиграть, но хуже, или замена). Пропуск 1-3 туров.
 • Средняя: Растяжение. Замена обязательна. Пропуск 4-8 туров.
 • Тяжелая: Разрыв/Перелом. Пропуск 8+туров.

4. Правила реализма (ВАЖНО)
 * Игнорировать: Нереалистичные действия («телепортация», «бег без усталости»), гарантии результата («мы точно забьем»), указание точного времени событий, тексты не на русском языке.
 * Замены: Игрокам нужно время на адаптацию (сразу результат не дают).
 * Результат: Высокий xG и доминация не гарантируют победу.

ВВОДНЫЕ ДАННЫЕ:
{match_input_data}

СТРУКТУРА ОТВЕТА (ПРОТОКОЛ):
1. Параметры матча
 * Погода: [Состояние и влияние]
 * Судья: [Имя/Тип и строгость]
2. Хронология матча
Опиши ход игры, учитывая тактики.
 * События: Голы, карточки (ЖК/КК), травмы (указать срок), VAR, офсайды, стычки (добавить компенс. время).
 * Важно: Реализуй не все моменты. Возможны сенсации. Комментарии матча каждые 5'-10'.
 * Пример: ГОЛ X:X. {home_name} или {away_name} (описание самого гола)
3. Итоговый протокол (Статистика)
 * Счет: X - Y
 * Действия абсолютно всех игроков: (Формат: Голы | Ассисты | Отборы | Сэйвы) | процент усталости (максимум до 8%). Указывать для всех, без исключения.
 * Оценки: Рейтинг за матч абсолютно всем игрокам, также описание каждого игрока (полезные действия или неудачные действия предоставив пример из матча. вкратце).
 * Разделение на клубы: Перед оценками игроков надо написать клуб. Например: Клуб: {home_name} и также с {away_name}
4. Анализ
 * Краткий итог: почему победил/проиграл (тактика, удача, судья, провал лидера).
 * Интересные факты/моменты.
5. Командная статистика 
• Общий xG
• Владение мячом (%)
• Точность и общее количество передач (%)
• Удары (всего) / в створ
• Угловые
• Штрафные
• Фолы / Офсайды
• Желтые / Красные карточки 
• Сейвы / Блоки
• Отборы / Перехваты
• Общие обводки
• Упущенные явные голевые моменты
6. Кратко кто забил/асситировал/время: 
- ?' Игрок (Игрок)
"""

# ================= СОСТОЯНИЯ =================
class SimMatch(StatesGroup):
    home_name = State()
    away_name = State()
    stadium = State()
    home_lineup = State()
    away_lineup = State()
    home_tactic = State()
    away_tactic = State()

class CleanState(StatesGroup):
    tactic = State()

# ================= ЛОГИКА =================

async def call_groq(prompt, system_text):
    try:
        res = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"Ошибка API: {e}"

async def log(msg, user):
    try:
        if LOG_GROUP_ID == 0: return
        text = f"👤 {user}\n\n{msg}"
        if len(text) > 4000:
            for i in range(0, len(text), 4000): await bot.send_message(LOG_GROUP_ID, text[i:i+4000])
        else: await bot.send_message(LOG_GROUP_ID, text)
    except: pass

@dp.message(CommandStart())
async def start(m: types.Message):
    await m.answer("Бот запущен. Выберите действие:", reply_markup=main_kb())

# --- ЧИСТКА ---
@dp.message(F.text == "Чистка Тактик")
async def cl_1(m: types.Message, state: FSMContext):
    await state.set_state(CleanState.tactic)
    await m.answer("Пришли тактику для чистки:")

@dp.message(CleanState.tactic)
async def cl_2(m: types.Message, state: FSMContext):
    await log(f"ЗАПРОС ЧИСТКИ:\n{m.text}", m.from_user.full_name)
    res = await call_groq(CLEAN_TACTIC_TEMPLATE.format(user_tactic=m.text), "Ты технический футбольный аналитик.")
    await m.answer(res)
    await log(f"РЕЗУЛЬТАТ ЧИСТКИ:\n{res}", "ИИ")
    await state.clear()

# --- СИМУЛЯЦИЯ ---
@dp.message(F.text == "Симуляция Матча")
async def s1(m: types.Message, state: FSMContext):
    await state.set_state(SimMatch.home_name)
    await m.answer("1️⃣ Название ХОЗЯЕВ:")

@dp.message(SimMatch.home_name)
async def s2(m: types.Message, state: FSMContext):
    await state.update_data(h_n=m.text)
    await state.set_state(SimMatch.away_name)
    await m.answer("2️⃣ Название ГОСТЕЙ:")

@dp.message(SimMatch.away_name)
async def s3(m: types.Message, state: FSMContext):
    await state.update_data(a_n=m.text)
    await state.set_state(SimMatch.stadium)
    await m.answer("3️⃣ Стадион / Место проведения:")

@dp.message(SimMatch.stadium)
async def s4(m: types.Message, state: FSMContext):
    await state.update_data(std=m.text)
    await state.set_state(SimMatch.home_lineup)
    d = await state.get_data()
    await m.answer(f"4️⃣ Состав, рейтинги и усталость {d['h_n']}:")

@dp.message(SimMatch.home_lineup)
async def s5(m: types.Message, state: FSMContext):
    await state.update_data(h_l=m.text)
    await state.set_state(SimMatch.away_lineup)
    d = await state.get_data()
    await m.answer(f"5️⃣ Состав, рейтинги и усталость {d['a_n']}:")

@dp.message(SimMatch.away_lineup)
async def s6(m: types.Message, state: FSMContext):
    await state.update_data(a_l=m.text, h_t="") # Сброс буфера тактики
    await state.set_state(SimMatch.home_tactic)
    d = await state.get_data()
    await m.answer(f"6️⃣ Присылай ТАКТИКУ {d['h_n']}.\nМожно несколькими сообщениями. В конце нажми кнопку «Готово».", reply_markup=done_kb())

@dp.message(SimMatch.home_tactic)
async def collect_h(m: types.Message, state: FSMContext):
    if m.text == "✅ Готово (Конец текста)":
        d = await state.get_data()
        await state.update_data(a_t="")
        await state.set_state(SimMatch.away_tactic)
        await m.answer(f"7️⃣ Теперь ТАКТИКУ {d['a_n']}.\nВ конце также нажми «Готово».", reply_markup=done_kb())
        return
    data = await state.get_data()
    await state.update_data(h_t=data.get("h_t", "") + "\n" + m.text)
    await m.answer("📥 Принял часть тактики...")

@dp.message(SimMatch.away_tactic)
async def collect_a(m: types.Message, state: FSMContext):
    if m.text == "✅ Готово (Конец текста)":
        d = await state.get_data()
        
        # Формируем блок вводных данных
        match_data = (
            f"Хозяева ({d['h_n']}):\n * Состав и рейтинги: {d['h_l']}\n * Тактика: {d['h_t']}\n\n"
            f"Гости ({d['a_n']}):\n * Состав и рейтинги: {d['a_l']}\n * Тактика: {d['a_t']}"
        )
        
        await log(f"ЗАПРОС СИМУЛЯЦИИ:\n{match_data}", m.from_user.full_name)
        await m.answer("⏳ Симулирую матч по новому протоколу...", reply_markup=main_kb())
        
        # Вызов ИИ с новым шаблоном
        full_prompt = SIMULATION_FULL_TEMPLATE.format(
            home_name=d['h_n'],
            away_name=d['a_n'],
            stadium=d['std'],
            match_input_data=match_data
        )
        
        system_inst = "Ты — профессиональный футбольный аналитик и симулятор матчей. Твоя задача — выдать полный и реалистичный протокол матча по всем пунктам структуры."
        res = await call_groq(full_prompt, system_inst)
        
        if len(res) > 4000:
            for i in range(0, len(res), 4000): await m.answer(res[i:i+4000])
        else: await m.answer(res)
        
        await log(f"ИТОГ СИМУЛЯЦИИ:\n{res}", "ИИ")
        await state.clear()
        return
    data = await state.get_data()
    await state.update_data(a_t=data.get("a_t", "") + "\n" + m.text)
    await m.answer("📥 Принял часть тактики...")

async def main():
    asyncio.create_task(start_webserver())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
