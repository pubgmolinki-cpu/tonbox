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

# ================= ВЕБ-СЕРВЕР ДЛЯ RENDER (ВАРИАНТ 2) =================
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

# ================= ПОЛНЫЕ ШАБЛОНЫ (БЕЗ СОКРАЩЕНИЙ) =================

CLEAN_TACTIC_TEMPLATE = """Бот, проанализируй и отредактируй эту тактику.

Исключи из неё:
 * Любые нереалистичные действия и отсылки к истории подготовки или конкретному сопернику.
 * Психологические оценки, высокую боевую готовность и абстрактные понятия (дух, характер, интуиция, химия).
 * Глаголы неуверенности и попытки (стараться, пытаться, стремиться, пробовать) — заменяй их на конкретные действия.
 * Любые метафоры, журналистские штампы и идиомы.
 * Субъективные оценочные прилагательные (опасный, уверенный, рискованный, грамотный).
 * Слова 'цель', 'стратегия', 'задача' и эпитеты.

Если какие-то принципы изложены избыточно, сделай формулировки сухими, императивными и технически точными. Используй терминологию (полуфланг, зона 14, низкий блок и т.д.), не меняя при этом структуру модели. Отправь мне финальный текст.

Если этого всего нет, просто скажи, что тактика чистая и не подлежит чистке

Вот сама тактика:
{user_tactic}"""

SIMULATION_FULL_TEMPLATE = """📝 ПОЛНАЯ СИМУЛЯЦИЯ МАТЧА (90 МИНУТ)

В этом чате ты комментируешь мои матчи. Твоя задача — провести полную симуляцию от 0 до 90 минуты, включая оба тайма и итоги.

Начинай будто идёт настоящий матч: где проходит игра, погода, атмосфера стадиона, стартовые составы команд, игроки вышли на поле, разминаются перед матчем, имя комментатора:

‼️ Комментируй каждые 6 минут, пример:
0’

6’

Я даю тебе составы, тактики и данные — ты симулируешь матч между командами.

---

## ⚙️ ПАРАМЕТРЫ СИМУЛЯЦИИ

При симуляции матча учитывай:
• 🧠 Тактика — 75%
• ⭐ Рейтинг игроков — 15%
• 🥵 Усталость — 10%

### Пояснение:

Тактика — главный фактор. Она определяет:
• инициативу
• стиль игры
• количество моментов
• итоговый результат

Рейтинг влияет на индивидуальные эпизоды и реализацию.
Усталость отражает физику, мораль и концентрацию.

Домашнее поле даёт минимальный бонус к качеству игры (~2%), но не решает исход.

❗ Важно

Перед началом атаки обязательно нужно описать, как именно она началась.

Пример оформления:

12’ Игрок А отобрал мяч у Игрока Б, ускорился по флангу, обыграл защитника и сделал навес в штрафную…

Далее обязательно указать завершение эпизода:

12’ — Гол ⚽
12’ — Сейв вратаря 🧤
12’ — Отор 🛡
12’ — Удар мимо
12’ — Блок защитника

Каждая атака должна быть логично описана:
начало → развитие → итог эпизода.

Гол может быть забит в любое время, так и в начале матча, так и в конце.

Без описания начала атака засчитана не будет.

---

## 📅 СЕЗОН И ТРАВМЫ

Игровой сезон длится 3 недели.

• Полсезона = 1,5 недели
• Все травмы рассчитываются относительно сезона
• Если игрок получает травму — обязательно указывать срок восстановления в формате сезона

Примеры:
• травма на полсезона = 1,5 недели вне игры
• травма на 1 сезон = 3 недели
• лёгкая травма = несколько дней.

Травма чаще всего может быть легкая, реже полсезона.

Травмы случаются редко, но если матч эмоциональный, то шанс травмы вырастает.

Если игрок получил травму — комментатор обязательно прямо сообщает срок отсутствия.

---

## 📊 РЕЙТИНГИ И УСТАЛОСТЬ

Рейтинги игроков:
• 99 — легенда
• 90 — элита
• 85 — звезда
• 80 — высокий уровень
• 70 — средний
• 60 — профи ниже среднего
• 50 — новичок
• 40 — начинающий 

Усталость:
• 0% — пик формы
• 30% — лёгкий спад
• 50% — заметные ошибки
• 70% — низкая эффективность
• 100% — почти не играет

⚠️ Усталость за матч не растёт более чем на 15%
⚠️ У вратаря усталость растёт меньше

---

## 😰 ДАВЛЕНИЕ ТРИБУН (МАНДРАЖ)

Если стадион заполнен полностью, игроки с низким рейтингом испытывают психологическое давление. Матч описывай не сухо, но и не как роман
• Пиши как реальный комментатор
• Не превращай матч в цирк
• Комментируй каждые 6 минут
• Соблюдай футбольную логику
• Все игровые механики (сезон, травмы, эмоции, мандраж) действуют ДО ФИНАЛЬНОГО СВИСТКА

Снижение точности передач:

• рейтинг 50 → −11% точности
• рейтинг 60 → −6%
• рейтинг 70 → −3%
• рейтинг выше 70 → почти нет мандража

Комментатор может отмечать нервозность, ошибки, неточные передачи.

---

## ⚡ ЭМОЦИОНАЛЬНАЯ ШКАЛА МАТЧА

Если происходят сильные эмоциональные события — временно меняется игра команд.

### Поздний гол (последние минуты матча)

Команда, забившая:
• +10% ко всем характеристикам на короткий период (эйфория)

Команда, пропустившая:
• падает концентрация
• больше ошибок
• риск паники в обороне

### Судейская несправедливость (например, очевидный непоставленный пенальти)

Пострадавшая команда:
• злится
• играет агрессивнее
• чаще фолит
• выше риск жёлтых и красных
• но возрастает напор в атаке

Комментатор должен эмоционально описывать изменение настроения.

---

## 👥 СОСТАВЫ И ТАКТИКИ (ДАННЫЕ)
{match_input_data}

---

## 🎙 СИМУЛЯЦИЯ МАТЧА (0'–90')
ВАЖНО: Опиши события ПЕРВОГО и ВТОРОГО тайма в одном ответе. Не останавливайся после 45 минуты. Продолжай симуляцию до финального свистка, учитывая нарастающую усталость игроков, тактики и замены. Комментируй каждые 6 минут.

---

## 🧾 ИТОГ МАТЧА

@projectRFPT | ИТОГОВЫЙ СЧЕТ
MVP, ПОЛНАЯ СТАТИСТИКА, ОЦЕНКИ ИГРОКОВ (от 5.0 до 10.0) с описанием полезных действий и % усталости.
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
    await m.answer("Бот запущен. Выберите действие в меню:", reply_markup=main_kb())

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
    await m.answer("3️⃣ Стадион:")

@dp.message(SimMatch.stadium)
async def s4(m: types.Message, state: FSMContext):
    await state.update_data(std=m.text)
    await state.set_state(SimMatch.home_lineup)
    d = await state.get_data()
    await m.answer(f"4️⃣ Состав {d['h_n']}:")

@dp.message(SimMatch.home_lineup)
async def s5(m: types.Message, state: FSMContext):
    await state.update_data(h_l=m.text)
    await state.set_state(SimMatch.away_lineup)
    d = await state.get_data()
    await m.answer(f"5️⃣ Состав {d['a_n']}:")

@dp.message(SimMatch.away_lineup)
async def s6(m: types.Message, state: FSMContext):
    await state.update_data(a_l=m.text, h_t="") # Сброс буфера тактики
    await state.set_state(SimMatch.home_tactic)
    d = await state.get_data()
    await m.answer(f"6️⃣ Присылай тактику {d['h_n']}.\nМожно несколькими сообщениями. В конце нажми кнопку «Готово».", reply_markup=done_kb())

@dp.message(SimMatch.home_tactic)
async def collect_h(m: types.Message, state: FSMContext):
    if m.text == "✅ Готово (Конец текста)":
        d = await state.get_data()
        await state.update_data(a_t="")
        await state.set_state(SimMatch.away_tactic)
        await m.answer(f"7️⃣ Теперь тактику {d['a_n']}.\nВ конце также нажми «Готово».", reply_markup=done_kb())
        return
    data = await state.get_data()
    await state.update_data(h_t=data.get("h_t", "") + "\n" + m.text)
    await m.answer("📥 Принял часть тактики...")

@dp.message(SimMatch.away_tactic)
async def collect_a(m: types.Message, state: FSMContext):
    if m.text == "✅ Готово (Конец текста)":
        d = await state.get_data()
        data_block = f"🔴 ХОЗЯЕВА: {d['h_n']}\n{d['h_l']}\nТактика: {d['h_t']}\n\n🔵 ГОСТИ: {d['a_n']}\n{d['a_l']}\nТактика: {d['a_t']}\n\n🏟 Стадион: {d['std']}"
        
        await log(f"ДАННЫЕ МАТЧА ДЛЯ ИИ:\n{data_block}", m.from_user.full_name)
        await m.answer("⏳ Симулирую ПОЛНЫЙ МАТЧ (90 минут)...\nПожалуйста, подождите.", reply_markup=main_kb())
        
        system_inst = "Ты — легендарный футбольный комментатор. Твоя задача — выдать ОДИН подробный отчет, покрывающий весь матч от 0 до 90+ минуты. Не останавливайся после первого тайма."
        res = await call_groq(SIMULATION_FULL_TEMPLATE.format(match_input_data=data_block), system_inst)
        
        if len(res) > 4000:
            for i in range(0, len(res), 4000): await m.answer(res[i:i+4000])
        else: await m.answer(res)
        
        await log(f"ИТОГ МАТЧА:\n{res}", "ИИ")
        await state.clear()
        return
    data = await state.get_data()
    await state.update_data(a_t=data.get("a_t", "") + "\n" + m.text)
    await m.answer("📥 Принял часть тактики...")

async def main():
    # Запуск фоновой задачи для порта
    asyncio.create_task(start_webserver())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
