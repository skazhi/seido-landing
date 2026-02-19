"""
Seido Bot - Обработчики команд
"""
from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from db import db
from config import PROJECT_NAME, PROJECT_TAGLINE

router = Router()


# ============================================
# МАШИНА СОСТОЯНИЙ: Регистрация
# ============================================
class Registration(StatesGroup):
    waiting_for_name = State()
    waiting_for_birth_date = State()
    waiting_for_gender = State()
    waiting_for_city = State()


# ============================================
# КЛАВИАТУРЫ
# ============================================
def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Основная клавиатура"""
    keyboard = [
        [KeyboardButton(text="📊 Мои результаты"), KeyboardButton(text="📈 Статистика")],
        [KeyboardButton(text="🏃 Сравнение"), KeyboardButton(text="📅 Календарь")],
        [KeyboardButton(text="➕ Добавить забег"), KeyboardButton(text="❓ Помощь")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_gender_keyboard() -> ReplyKeyboardMarkup:
    """Выбор пола"""
    keyboard = [
        [KeyboardButton(text="Мужской"), KeyboardButton(text="Женский")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_consent_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура согласия на обработку ПДн"""
    keyboard = [
        [KeyboardButton(text="✅ Принять")],
        [KeyboardButton(text="❌ Отмена")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_delete_confirmation_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура подтверждения удаления"""
    keyboard = [
        [KeyboardButton(text="✅ Удалить")],
        [KeyboardButton(text="❌ Отмена")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)


# ============================================
# КОМАНДА /start
# ============================================
@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    """Приветствие и регистрация"""
    user = await db.get_runner_by_telegram_id(message.from_user.id)

    if user:
        # Пользователь уже зарегистрирован
        await message.answer(
            f"👋 С возвращением, {user['first_name']}!\n\n"
            f"Добро пожаловать в {PROJECT_NAME} — {PROJECT_TAGLINE}.\n\n"
            f"Используй кнопки ниже для навигации.",
            reply_markup=get_main_keyboard()
        )
    else:
        # Запрос согласия на обработку ПДн
        await message.answer(
            f"👋 Привет! Я бот {PROJECT_NAME}.\n\n"
            f"{PROJECT_TAGLINE}\n\n"
            f"Я помогу тебе:\n"
            "• Найти все твои результаты в одном месте\n"
            "• Смотреть личные рекорды на любых дистанциях\n"
            "• Сравнивать себя с другими бегунами\n"
            "• Следить за предстоящими забегами\n\n"
            "─────────────────────────────\n\n"
            "📋 **Перед регистрацией — важное соглашение**\n\n"
            "Нажимая «✅ Принять», вы даёте согласие на обработку "
            "ваших персональных данных:\n\n"
            "• Фамилия, имя, дата рождения\n"
            "• Город проживания\n"
            "• Спортивные результаты на забегах\n\n"
            "**Цель обработки**:\n"
            "✅ Сохранение ваших результатов в истории\n"
            "✅ Поиск ваших результатов по фамилии\n"
            "✅ Формирование статистики и рейтингов\n\n"
            "**Ваши права**:\n"
            "📌 Вы можете запросить удаление всех данных в любой момент\n"
            "📌 Вы можете отозвать согласие через поддержку\n"
            "📌 Данные не передаются третьим лицам\n\n"
            "Полная версия: https://skazhi.github.io/seido-landing/docs/offer.md",
            reply_markup=get_consent_keyboard()
        )
        await state.set_state('waiting_for_consent')


@router.message(F.text == "✅ Принять")
async def process_consent(message: types.Message, state: FSMContext):
    """Обработка согласия"""
    await state.update_data(consent_given=True)
    
    await message.answer(
        "✅ Спасибо! Теперь давайте зарегистрируемся.\n\n"
        "Как тебя зовут?\n"
        "Напиши фамилию и имя (например: Иванов Иван)"
    )
    await state.set_state(Registration.waiting_for_name)


@router.message(F.text == "❌ Отмена")
async def cancel_consent(message: types.Message, state: FSMContext):
    """Отказ от согласия"""
    await state.clear()
    await message.answer(
        "❌ Понимаем. Без согласия мы не можем обрабатывать ваши данные.\n\n"
        "Если передумаете — просто напишите /start"
    )


# ============================================
# РЕГИСТРАЦИЯ: Имя
# ============================================
@router.message(Registration.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    """Обработка имени"""
    name_parts = message.text.strip().split()
    
    if len(name_parts) < 2:
        await message.answer(
            "⚠️ Пожалуйста, напиши фамилию и имя через пробел.\n"
            "Например: Иванов Иван"
        )
        return
    
    await state.update_data(
        last_name=name_parts[0],
        first_name=name_parts[1],
        middle_name=name_parts[2] if len(name_parts) > 2 else None
    )
    
    await message.answer(
        "📅 Когда ты родился?\n"
        "Напиши дату в формате ДД.ММ.ГГГГ (например: 15.05.1990)"
    )
    await state.set_state(Registration.waiting_for_birth_date)


# ============================================
# РЕГИСТРАЦИЯ: Дата рождения
# ============================================
@router.message(Registration.waiting_for_birth_date)
async def process_birth_date(message: types.Message, state: FSMContext):
    """Обработка даты рождения"""
    from datetime import datetime
    
    try:
        birth_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат даты.\n"
            "Пожалуйста, используй формат ДД.ММ.ГГГГ (например: 15.05.1990)"
        )
        return
    
    await state.update_data(birth_date=birth_date)
    
    await message.answer(
        "👤 Твой пол:",
        reply_markup=get_gender_keyboard()
    )
    await state.set_state(Registration.waiting_for_gender)


# ============================================
# РЕГИСТРАЦИЯ: Пол
# ============================================
@router.message(Registration.waiting_for_gender)
async def process_gender(message: types.Message, state: FSMContext):
    """Обработка пола"""
    gender_map = {"Мужской": "M", "Женский": "F"}
    gender = gender_map.get(message.text.strip())
    
    if not gender:
        await message.answer("⚠️ Пожалуйста, выбери пол из кнопок ниже.")
        return
    
    await state.update_data(gender=gender)
    
    await message.answer(
        "🏙 В каком городе ты живёшь?\n"
        "Напиши название города (например: Москва)"
    )
    await state.set_state(Registration.waiting_for_city)


# ============================================
# РЕГИСТРАЦИЯ: Город
# ============================================
@router.message(Registration.waiting_for_city)
async def process_city(message: types.Message, state: FSMContext):
    """Обработка города и завершение регистрации"""
    city = message.text.strip()
    data = await state.get_data()
    
    # Создаём бегуна в базе
    await db.create_runner(
        telegram_id=message.from_user.id,
        first_name=data['first_name'],
        last_name=data['last_name'],
        birth_date=data['birth_date'],
        gender=data['gender'],
        city=city
    )
    
    await state.clear()
    
    await message.answer(
        f"✅ {data['first_name']}, регистрация завершена!\n\n"
        f"Теперь ты можешь:\n"
        "• Посмотреть свои результаты (/myresults)\n"
        "• Узнать общую статистику (/stats)\n"
        "• Сравнить себя с другими (/compare)\n"
        "• Предложить забег для добавления (/addrace)\n\n"
        "🏃‍♂️ Поехали!",
        reply_markup=get_main_keyboard()
    )


# ============================================
# КОМАНДА /myresults - Мои результаты
# ============================================
@router.message(Command("myresults"))
@router.message(F.text == "📊 Мои результаты")
async def cmd_myresults(message: types.Message):
    """Показать результаты пользователя"""
    user = await db.get_runner_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer(
            "⚠️ Сначала нужно зарегистрироваться.\n"
            "Напиши /start"
        )
        return
    
    results = await db.get_runner_results(user['id'])
    
    if not results:
        await message.answer(
            f"😔 {user['first_name']}, у тебя пока нет результатов в базе.\n\n"
            "Мы сейчас наполняем базу результатами московских забегов.\n"
            "Скоро ты сможешь найти свои результаты!\n\n"
            "Если хочешь, можешь предложить забег для добавления: /addrace"
        )
        return
    
    # Формируем сообщение с результатами
    response = f"🏃‍♂️ Твои результаты, {user['first_name']}:\n\n"
    
    for res in results[:10]:  # Показываем последние 10
        time_str = str(res['finish_time'] or f"{res['finish_time_seconds']} сек")
        place_str = f"#{res['overall_place']}" if res['overall_place'] else ""
        total_str = f"из {res['total_runners']}" if res['total_runners'] else ""
        
        response += (
            f"📍 **{res['race_name']}** ({res['organizer']})\n"
            f"📅 {res['race_date']}\n"
            f"🏁 Дистанция: {res['distance']}\n"
            f"⏱ Время: {time_str}\n"
            f"🥇 Место: {place_str} {total_str}\n\n"
        )
    
    if len(results) > 10:
        response += f"... и ещё {len(results) - 10} результатов\n"
    
    await message.answer(response)


# ============================================
# КОМАНДА /stats - Общая статистика
# ============================================
@router.message(Command("stats"))
@router.message(F.text == "📈 Статистика")
async def cmd_stats(message: types.Message):
    """Показать общую статистику"""
    total_runners = await db.get_total_runners()
    total_races = await db.get_total_races()
    total_results = await db.get_total_results()
    
    await message.answer(
        f"📊 **Статистика {PROJECT_NAME}**\n\n"
        f"🏃‍♂️ Бегунов в базе: {total_runners}\n"
        f"🏁 Забегов: {total_races}\n"
        f"📈 Результатов: {total_results}\n\n"
        f"Мы только начинаем, но уже собираем данные!\n\n"
        "Хочешь увидеть топ бегунов по количеству результатов?"
    )


# ============================================
# КОМАНДА /compare - Сравнение
# ============================================
@router.message(Command("compare"))
@router.message(F.text == "🏃 Сравнение")
async def cmd_compare(message: types.Message):
    """Сравнение с другим бегуном"""
    user = await db.get_runner_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer("⚠️ Сначала зарегистрируйся: /start")
        return
    
    await message.answer(
        "🏃 С кем хочешь сравниться?\n\n"
        "Напиши фамилию и имя бегуна (например: Иванов Иван)\n"
        "Или ответь на сообщение другого пользователя."
    )


# ============================================
# КОМАНДА /addrace - Добавить забег
# ============================================
class AddRace(StatesGroup):
    waiting_for_race_name = State()


@router.message(Command("addrace"))
@router.message(F.text == "➕ Добавить забег")
async def cmd_addrace(message: types.Message, state: FSMContext):
    """Предложить забег для добавления"""
    await message.answer(
        "📝 Хочешь добавить забег в базу?\n\n"
        "Напиши название забега и дату (если знаешь).\n"
        "Например: Пятерка в Парке 15.03.2026\n\n"
        "Или просто название, если даты нет."
    )
    await state.set_state(AddRace.waiting_for_race_name)


@router.message(AddRace.waiting_for_race_name)
async def process_race_name(message: types.Message, state: FSMContext):
    """Обработка названия забега"""
    race_text = message.text.strip()

    # Простой парсинг даты из текста
    race_date = None
    race_name = race_text

    import re
    date_match = re.search(r'\d{2}\.\d{2}\.\d{4}', race_text)
    if date_match:
        race_date = date_match.group()
        race_name = race_text.replace(race_date, '').strip()

    # Сохраняем заявку
    await db.submit_race(
        submitted_by=message.from_user.id,
        race_name=race_name,
        race_date=race_date
    )

    await state.clear()

    await message.answer(
        "✅ Спасибо! Твоя заявка на добавление забега сохранена.\n\n"
        "Администратор проверит и добавит забег в базу."
    )


# ============================================
# КОМАНДА /help - Помощь
# ============================================
@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: types.Message):
    """Справка"""
    await message.answer(
        f"❓ **Помощь по {PROJECT_NAME}**\n\n"
        "📋 **Команды:**\n"
        "/start - Регистрация и главное меню\n"
        "/myresults - Мои результаты\n"
        "/stats - Общая статистика\n"
        "/compare - Сравнение с другим бегуном\n"
        "/addrace - Предложить забег\n"
        "/delete - Удалить мои данные\n"
        "/help - Эта справка\n\n"
        "📱 **Кнопки:**\n"
        "📊 Мои результаты - показать твои результаты\n"
        "📈 Статистика - общая статистика проекта\n"
        "🏃 Сравнение - сравнить с другим бегуном\n"
        "📅 Календарь - предстоящие забеги\n"
        "➕ Добавить забег - предложить новый забег\n"
        "❓ Помощь - эта справка\n\n"
        "🔒 **Конфиденциальность:**\n"
        "Ваши данные защищены. Вы можете удалить их в любой момент командой /delete.\n\n"
        "Полная политика: https://skazhi.github.io/seido-landing/docs/offer.md\n\n"
        "💡 Есть вопросы или идеи? Пиши создателю: @Skazhi"
    )


# ============================================
# КАЛЕНДАРЬ ЗАБЕГОВ
# ============================================
@router.message(F.text == "📅 Календарь")
async def cmd_calendar(message: types.Message):
    """Календарь предстоящих забегов"""
    races = await db.get_upcoming_races(limit=5)

    if not races:
        await message.answer(
            "📅 Календарь забегов скоро появится!\n\n"
            "Мы собираем информацию о предстоящих стартах."
        )
        return

    response = "📅 **Предстоящие забеги:**\n\n"

    for race in races:
        response += (
            f"🏁 **{race['name']}**\n"
            f"📅 {race['date']}\n"
            f"📍 {race['location'] or 'Точное место уточняется'}\n"
            f"🏢 Организатор: {race['organizer'] or 'Не указан'}\n\n"
        )

    await message.answer(response)


# ============================================
# КОМАНДА /delete - Удаление данных
# ============================================
@router.message(Command("delete"))
async def cmd_delete(message: types.Message, state: FSMContext):
    """Удаление всех данных пользователя"""
    user = await db.get_runner_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("⚠️ У нас нет ваших данных. Сначала зарегистрируйтесь: /start")
        return

    await message.answer(
        "⚠️ **Вы уверены?**\n\n"
        "Это действие удалит:\n"
        "• Ваш профиль\n"
        "• Все ваши результаты\n"
        "• Подписки на забеги\n\n"
        "Восстановить данные будет невозможно.\n\n"
        "Нажмите «✅ Удалить» для подтверждения или «❌ Отмена»",
        reply_markup=get_delete_confirmation_keyboard()
    )
    await state.set_state('waiting_for_delete_confirm')


@router.message(F.text == "✅ Удалить")
async def confirm_delete(message: types.Message, state: FSMContext):
    """Подтверждение удаления"""
    user = await db.get_runner_by_telegram_id(message.from_user.id)
    
    if user:
        await db.delete_runner(user['id'])
    
    await state.clear()
    
    await message.answer(
        "✅ Ваши данные удалены из базы.\n\n"
        "Если захотите вернуться — напишите /start"
    )


@router.message(F.text == "❌ Отмена")
async def cancel_delete(message: types.Message, state: FSMContext):
    """Отмена удаления"""
    await state.clear()
    await message.answer("✅ Удаление отменено. Ваши данные сохранены.")
