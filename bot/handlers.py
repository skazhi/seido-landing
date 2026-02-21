"""
Seido Bot - Обработчики команд
"""
from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
)

from db import db
from config import PROJECT_NAME, PROJECT_TAGLINE, ADMINS
from parsers.scheduler import run_parse

router = Router()

# Хранилище параметров поиска для пагинации (user_id -> filters)
_last_search: dict[int, dict] = {}
_last_history_search: dict[int, dict] = {}


# ============================================
# МАШИНА СОСТОЯНИЙ: Регистрация
# ============================================
class Registration(StatesGroup):
    waiting_for_name = State()
    waiting_for_birth_date = State()
    waiting_for_gender = State()
    waiting_for_city = State()
    waiting_for_city_manual = State()
    waiting_for_club = State()


# ============================================
# КЛАВИАТУРЫ
# ============================================

# Популярные города для выбора (с учётом забегов в базе)
CITIES = [
    "Москва", "Санкт-Петербург", "Казань", "Сочи", "Краснодар",
    "Нижний Новгород", "Екатеринбург", "Новосибирск", "Тула",
    "Ростов-на-Дону", "Когалым", "Волгоград", "Воронеж", "Самара",
    "Уфа", "Красноярск", "Геленджик", "Архыз", "Сириус",
]


def _escape_md(text: str) -> str:
    """Экранирование _ и * — иначе Markdown ломается и сообщение не отправляется"""
    if not text:
        return text
    return str(text).replace("_", "\\_").replace("*", "\\*")


def _find_closest_city(text: str) -> str | None:
    """Найти ближайший город по опечатке (или None если точное совпадение)"""
    import difflib
    t = text.strip()
    if not t:
        return None
    for c in CITIES:
        if c.lower() == t.lower():
            return None  # точное совпадение
    match = difflib.get_close_matches(t, CITIES, n=1, cutoff=0.72)
    return match[0] if match else None


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Основная клавиатура — все команды бота"""
    keyboard = [
        [KeyboardButton(text="📊 Мои результаты"), KeyboardButton(text="📈 Статистика")],
        [KeyboardButton(text="📅 Календарь"), KeyboardButton(text="🔍 Поиск"), KeyboardButton(text="📜 История")],
        [KeyboardButton(text="🏃 Сравнение"), KeyboardButton(text="➕ Добавить забег")],
        [KeyboardButton(text="🔎 Найти результат"), KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="❓ Помощь")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_city_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура выбора города (популярные + «Другой»)"""
    row1 = [KeyboardButton(text=c) for c in CITIES[:5]]
    row2 = [KeyboardButton(text=c) for c in CITIES[5:10]]
    row3 = [KeyboardButton(text=c) for c in CITIES[10:15]]
    row4 = [KeyboardButton(text="Другой город")]
    keyboard = [row1, row2, row3, row4]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)


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
            "• ФИО, дата рождения, пол, город, клуб\n"
            "• Спортивные результаты на забегах\n\n"
            "Цель обработки:\n"
            "✅ Сохранение ваших результатов в истории\n"
            "✅ Поиск ваших результатов по фамилии\n"
            "✅ Формирование статистики и рейтингов\n\n"
            "**Ваши права:**\n"
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
        "Указывай данные так же, как в паспорте и в заявках на забеги — "
        "по ним мы ищем твои результаты в протоколах.\n\n"
        "ФИО (фамилия, имя, отчество):\n"
        "Например: Иванов Иван Иванович"
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
        "🏙 Город проживания:\n"
        "Выбери из списка или «Другой город» для ручного ввода:",
        reply_markup=get_city_keyboard()
    )
    await state.set_state(Registration.waiting_for_city)


# ============================================
# РЕГИСТРАЦИЯ: Город
# ============================================
@router.message(Registration.waiting_for_city, F.text == "Другой город")
async def process_city_other(message: types.Message, state: FSMContext):
    """Пользователь выбрал «Другой город» — запрос ручного ввода"""
    await message.answer(
        "✏️ Напиши название города вручную:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(Registration.waiting_for_city_manual)


@router.message(Registration.waiting_for_city_manual, F.text)
async def process_city_manual(message: types.Message, state: FSMContext):
    """Ручной ввод города с проверкой на опечатку"""
    text = message.text.strip()
    if not text:
        await message.answer("⚠️ Введи название города.")
        return
    suggested = _find_closest_city(text)
    if suggested:
        # Возможная опечатка — предлагаем исправление
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Да, {suggested}", callback_data=f"city_ok:{suggested}")],
            [InlineKeyboardButton(text="Нет, оставить как есть", callback_data=f"city_keep:{text}")],
        ])
        await message.answer(
            f"Вы имели в виду {suggested}?",
            reply_markup=kb
        )
        await state.update_data(pending_city=text)
        return
    await state.update_data(city=text)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Пропустить")]], resize_keyboard=True, one_time_keyboard=True)
    await message.answer(
        "🏃 Клуб или беговое сообщество (по желанию):\n"
        "Напиши название или нажми «Пропустить»",
        reply_markup=kb
    )
    await state.set_state(Registration.waiting_for_club)


@router.callback_query(F.data.startswith("city_ok:"))
async def cb_city_ok(callback: CallbackQuery, state: FSMContext):
    """Пользователь подтвердил предложенный город"""
    city = callback.data.split(":", 1)[1]
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.update_data(city=city)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Пропустить")]], resize_keyboard=True, one_time_keyboard=True)
    await callback.message.answer(
        "🏃 Клуб или беговое сообщество (по желанию):\n"
        "Напиши название или нажми «Пропустить»",
        reply_markup=kb
    )
    await state.set_state(Registration.waiting_for_club)
    await callback.answer()


@router.callback_query(F.data.startswith("city_keep:"))
async def cb_city_keep(callback: CallbackQuery, state: FSMContext):
    """Пользователь оставил введённый текст как есть"""
    city = callback.data.split(":", 1)[1]
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.update_data(city=city)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Пропустить")]], resize_keyboard=True, one_time_keyboard=True)
    await callback.message.answer(
        "🏃 Клуб или беговое сообщество (по желанию):\n"
        "Напиши название или нажми «Пропустить»",
        reply_markup=kb
    )
    await state.set_state(Registration.waiting_for_club)
    await callback.answer()


async def _finish_registration(chat_id: int, user_id: int, first_name: str, state: FSMContext, city: str, club: str, bot):
    """Завершение регистрации"""
    data = await state.get_data()
    await db.create_runner(
        telegram_id=user_id,
        first_name=data['first_name'],
        last_name=data['last_name'],
        middle_name=data.get('middle_name'),
        birth_date=data['birth_date'],
        gender=data['gender'],
        city=city,
        club_name=club or None,
    )
    await state.clear()
    await bot.send_message(
        chat_id,
        f"✅ {data['first_name']}, регистрация завершена!\n\n"
        f"Теперь ты можешь:\n"
        "• Посмотреть свои результаты (📊 Мои результаты)\n"
        "• Узнать общую статистику (📈 Статистика)\n"
        "• Сравнить себя с другими (🏃 Сравнение)\n"
        "• Предложить забег (➕ Добавить забег)\n\n"
        "🏃‍♂️ Поехали!",
        reply_markup=get_main_keyboard()
    )


@router.message(Registration.waiting_for_city, F.text)
async def process_city(message: types.Message, state: FSMContext):
    """Обработка города — выбор из кнопок"""
    city = message.text.strip()
    if city not in CITIES:
        await message.answer("⚠️ Выбери город из кнопок или нажми «Другой город».")
        return
    await state.update_data(city=city)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Пропустить")]], resize_keyboard=True, one_time_keyboard=True)
    await message.answer(
        "🏃 Клуб или беговое сообщество (по желанию):\n"
        "Напиши название или нажми «Пропустить»",
        reply_markup=kb
    )
    await state.set_state(Registration.waiting_for_club)


# ============================================
# РЕГИСТРАЦИЯ: Клуб
# ============================================
@router.message(Registration.waiting_for_club, F.text)
async def process_club(message: types.Message, state: FSMContext):
    """Обработка клуба и завершение регистрации"""
    club = message.text.strip()
    if club.lower() in ("пропустить", "нет", "skip"):
        club = ""
    data = await state.get_data()
    city = data.get("city", "")
    await _finish_registration(
        message.chat.id, message.from_user.id,
        data['first_name'], state, city, club, message.bot
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
        
        source_note = ""
        # Добавляем информацию об источнике, если есть
        if res.get('protocol_url'):
            source_note = f"\n📄 Источник: {res['protocol_url']}"
        elif res.get('organizer'):
            source_note = f"\n🏢 Организатор: {res['organizer']}"
        
        response += (
            f"📍 **{res['race_name']}** ({res['organizer']})\n"
            f"📅 {res['race_date']}\n"
            f"🏁 Дистанция: {res['distance']}\n"
            f"⏱ Время: {time_str}\n"
            f"🥇 Место: {place_str} {total_str}"
            f"{source_note}\n\n"
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
# НАЙТИ РЕЗУЛЬТАТ / ЗАЯВКА «ЭТО Я»
# ============================================
class FindResult(StatesGroup):
    waiting_for_name = State()


@router.message(Command("find_result"))
@router.message(F.text == "🔎 Найти результат")
async def cmd_find_result(message: types.Message, state: FSMContext):
    """Поиск результата по ФИО для привязки к профилю"""
    user = await db.get_runner_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("⚠️ Сначала зарегистрируйся: /start")
        return
    await message.answer(
        "🔎 **Найти результат**\n\n"
        "Напиши фамилию и имя (как в протоколе):\n"
        "Например: Иванов Иван"
    )
    await state.set_state(FindResult.waiting_for_name)


@router.message(FindResult.waiting_for_name, F.text)
async def process_find_result(message: types.Message, state: FSMContext):
    """Показать найденные результаты и кнопку «Это я»"""
    query = message.text.strip()
    if len(query) < 2:
        await message.answer("⚠️ Введи хотя бы 2 символа.")
        return

    results = await db.search_results_by_name(query, limit=15)
    if not results:
        await state.clear()
        await message.answer(
            "По твоему запросу ничего не найдено.\n\n"
            "Результаты подтягиваются из протоколов забегов. "
            "Если твоего забега ещё нет — предложи добавить: ➕ Добавить забег"
        )
        return

    user = await db.get_runner_by_telegram_id(message.from_user.id)
    text = "🔎 Найдено результатов:\n\n"
    for i, r in enumerate(results[:10], 1):
        name = f"{r.get('last_name', '')} {r.get('first_name', '')} {r.get('middle_name', '') or ''}".strip()
        time_s = r.get('finish_time') or "—"
        place = f"место {r.get('overall_place')}" if r.get('overall_place') else ""
        text += f"{i}. {name} — {r.get('race_name')} ({r.get('race_date')})\n"
        text += f"   {r.get('distance')} | {time_s} {place}\n"
        if r.get('protocol_url'):
            text += f"   Протокол: {r['protocol_url'][:60]}…\n"
        text += "\n"

    # Кнопки «Это я» для каждого результата (пока первые 5)
    buttons = []
    for r in results[:5]:
        rid = r.get('result_id')
        if rid:
            buttons.append([InlineKeyboardButton(
                text=f"Это я: {r.get('race_name', '')[:25]}… ({r.get('distance')})",
                callback_data=f"claim:{rid}"
            )])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
    await message.answer(text, reply_markup=kb)
    await state.clear()


@router.callback_query(F.data.startswith("claim:"))
async def cb_claim_result(callback: CallbackQuery):
    """Заявка «это я» — отправить на рассмотрение админу"""
    try:
        result_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка")
        return

    user = await db.get_runner_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Сначала зарегистрируйся")
        return

    res = await db.get_result_with_race(result_id)
    if not res:
        await callback.answer("Результат не найден")
        return

    # Проверка: результат уже привязан к этому пользователю?
    if res.get('runner_id') == user['id']:
        await callback.answer("Этот результат уже в твоём профиле")
        return

    claim_id = await db.add_result_claim(result_id, user['id'], callback.from_user.id)
    if not claim_id:
        await callback.answer("Заявка уже подана или ошибка")
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Заявка отправлена на рассмотрение")
    await callback.message.answer(
        "✅ Заявка «это я» отправлена.\n\n"
        "Администратор проверит и привяжет результат к твоему профилю. "
        "Ожидай уведомления."
    )

    # Уведомление админу
    for admin_id in ADMINS:
        if admin_id and admin_id != 0:
            try:
                await callback.bot.send_message(
                    admin_id,
                    f"🔎 **Новая заявка «это я»**\n\n"
                    f"Результат: {res.get('race_name')} | {res.get('distance')} | {res.get('finish_time')}\n"
                    f"Заявитель: {user['first_name']} {user['last_name']} (tg:{callback.from_user.id})\n\n"
                    f"/admin_claims — рассмотреть заявки"
                )
            except Exception:
                pass


# ============================================
# КОМАНДА /addrace - Добавить забег
# ============================================
class AddRace(StatesGroup):
    waiting_for_race_name = State()


class DeleteConfirm(StatesGroup):
    waiting = State()


class SearchInput(StatesGroup):
    waiting_for_query = State()


# ============================================
# КОМАНДА /profile - Мой профиль (личный кабинет)
# ============================================
@router.message(Command("profile"))
@router.message(F.text == "👤 Мой профиль")
async def cmd_profile(message: types.Message):
    """Карточка бегуна: данные + действия"""
    try:
        user = await db.get_runner_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("⚠️ Сначала зарегистрируйся: /start")
            return

        results = await db.get_runner_results(user['id'])
        subs = await db.get_runner_subscriptions(user['id'])

        parts = [user.get('last_name', ''), user.get('first_name', '')]
        if user.get('middle_name'):
            parts.append(user['middle_name'])
        name = " ".join(p for p in parts if p).strip() or "—"
        gender_str = "Мужской" if user.get('gender') == 'M' else "Женский" if user.get('gender') == 'F' else "—"
        city = user.get('city') or "—"
        club = user.get('club_name') or "—"

        birth_raw = user.get('birth_date')
        if birth_raw:
            try:
                from datetime import datetime, date
                s = str(birth_raw)[:10]
                dt = datetime.strptime(s, "%Y-%m-%d")
                birth = dt.strftime("%d.%m.%Y")
                today = date.today()
                bd = dt.date()
                age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
            except Exception:
                birth = str(birth_raw)[:10]
                age = "—"
        else:
            birth = "—"
            age = "—"

        text = (
        f"👤 **Мой профиль**\n\n"
        f"📋 {_escape_md(name)}\n"
        f"📅 Дата рождения: {_escape_md(str(birth))}\n"
        f"🎂 Полных лет: {_escape_md(str(age))}\n"
        f"👤 Пол: {_escape_md(gender_str)}\n"
        f"🏙 Город: {_escape_md(city)}\n"
        f"🏃 Клуб: {_escape_md(club)}\n\n"
        f"📊 Результатов в базе: {len(results)}\n"
        f"📌 Подписок на забеги: {len(subs)}\n"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏆 Личные рекорды", callback_data="profile:records")],
            [InlineKeyboardButton(text="💬 Обратная связь", callback_data="profile:feedback")],
            [InlineKeyboardButton(text="🗑 Удалить мои данные", callback_data="profile:delete")],
        ])
        await message.answer(text, reply_markup=kb)
    except Exception as e:
        import logging
        logging.exception("Ошибка в профиле")
        await message.answer(f"⚠️ Ошибка: {e}")


def _format_seconds(sec: int) -> str:
    """Секунды в ЧЧ:ММ:СС или ММ:СС"""
    if sec is None or sec < 0:
        return "—"
    h, rest = divmod(sec, 3600)
    m, s = divmod(rest, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}" if m > 0 else f"0:{s:02d}"


@router.callback_query(F.data == "profile:records")
async def cb_profile_records(callback: CallbackQuery):
    """Личные рекорды — только из базы результатов"""
    user = await db.get_runner_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Сначала зарегистрируйся")
        return

    bests = await db.get_runner_personal_bests(user['id'])
    if not bests:
        await callback.answer()
        await callback.message.answer(
            "🏆 Личные рекорды\n\n"
            "Пока нет результатов в базе. Рекорды появляются автоматически "
            "из протоколов забегов — мы не принимаем ручной ввод, чтобы сохранить честность."
        )
        return

    text = "🏆 Личные рекорды\n\n"
    text += "Рассчитаны только из результатов в базе (ручной ввод не предусмотрен).\n\n"
    for b in sorted(bests, key=lambda x: (x.get('distance') or '')):
        dist = b.get('distance', '?')
        sec = b.get('finish_time_seconds')
        time_str = b.get('finish_time') or _format_seconds(sec)
        race = b.get('race_name', '—')
        date = b.get('race_date', '')
        text += f"• {dist}: {time_str}\n  {race} ({date})\n\n"

    await callback.answer()
    await callback.message.answer(text)


@router.callback_query(F.data == "profile:feedback")
async def cb_profile_feedback(callback: CallbackQuery, state: FSMContext):
    """Обратная связь из профиля"""
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "💬 **Обратная связь**\n\n"
        "Напиши свои мысли, пожелания или сообщи о баге.\n"
        "Всё прочитаю и учту.\n\n"
        "Или /cancel для отмены."
    )
    await state.set_state(Feedback.waiting_for_text)
    await callback.answer()


@router.callback_query(F.data == "profile:delete")
async def cb_profile_delete(callback: CallbackQuery, state: FSMContext):
    """Удаление данных из профиля"""
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "⚠️ Вы уверены?\n\n"
        "Это удалит: профиль, результаты, подписки.\n"
        "Восстановить будет невозможно.\n\n"
        "Подтвердите ниже:",
        reply_markup=get_delete_confirmation_keyboard()
    )
    await state.set_state(DeleteConfirm.waiting)
    await callback.answer()


# ============================================
# КОМАНДА /feedback - Обратная связь (из профиля или /feedback)
# ============================================
class Feedback(StatesGroup):
    waiting_for_text = State()


@router.message(Command("feedback"))
async def cmd_feedback(message: types.Message, state: FSMContext):
    """Обратная связь от пользователя"""
    await message.answer(
        "💬 **Обратная связь**\n\n"
        "Напиши свои мысли, пожелания или сообщи о баге.\n"
        "Всё прочитаю и учту.\n\n"
        "Или нажми /cancel чтобы отменить."
    )
    await state.set_state(Feedback.waiting_for_text)


@router.message(Feedback.waiting_for_text, Command("cancel"))
@router.message(Feedback.waiting_for_text, F.text == "❌ Отмена")
async def cancel_feedback(message: types.Message, state: FSMContext):
    """Отмена отправки обратной связи"""
    await state.clear()
    await message.answer("✅ Отменено.")


@router.message(Feedback.waiting_for_text, F.text)
async def process_feedback(message: types.Message, state: FSMContext):
    """Обработка текста обратной связи"""
    text = message.text.strip()
    if len(text) < 5:
        await message.answer("⚠️ Напиши хотя бы пару слов (от 5 символов).")
        return

    user = await db.get_runner_by_telegram_id(message.from_user.id)
    runner_id = user['id'] if user else None

    await db.submit_feedback(
        telegram_id=message.from_user.id,
        text=text,
        runner_id=runner_id,
    )

    # Уведомление админу
    from config import ADMINS
    for admin_id in ADMINS:
        if admin_id and admin_id != 0:
            try:
                await message.bot.send_message(
                    admin_id,
                    f"💬 Обратная связь от {message.from_user.username or message.from_user.id}\n\n"
                    f"{text}"
                )
            except Exception:
                pass

    await state.clear()
    await message.answer(
        "✅ Спасибо! Твоё сообщение сохранено.\n\n"
        "Я обязательно его прочитаю."
    )


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
        f"❓ Помощь по {PROJECT_NAME}\n\n"
        "📋 **Команды:**\n"
        "/start - Регистрация и главное меню\n"
        "/myresults - Мои результаты\n"
        "/stats - Общая статистика\n"
        "/compare - Сравнение с другим бегуном\n"
        "/calendar - Предстоящие забеги (с листанием)\n"
        "/search - Поиск: город, дата, тип, дистанция\n"
        "/history - Прошедшие забеги (с поиском: /history город Москва)\n"
        "/addrace - Предложить забег\n"
        "/delete - Удалить мои данные\n"
        "/profile - Мой профиль (данные, обратная связь)\n"
        "/help - Эта справка\n\n"
        "📱 Кнопки меню:\n"
        "📊 Мои результаты | 📈 Статистика\n"
        "📅 Календарь | 🔍 Поиск | 📜 История\n"
        "🏃 Сравнение | ➕ Добавить забег\n"
        "🔎 Найти результат | 👤 Мой профиль | ❓ Помощь\n\n"
        "🔒 Конфиденциальность:\n"
        "Ваши данные защищены. Вы можете удалить их в любой момент командой /delete.\n\n"
        "Полная политика: https://skazhi.github.io/seido-landing/docs/offer.md\n\n"
        "💡 Есть вопросы или идеи? Пиши создателю: @Skazhi"
    )


# ============================================
# КАЛЕНДАРЬ ЗАБЕГОВ (с пагинацией и поиском)
# ============================================

def _format_race(race: dict, show_type: bool = False, show_protocol: bool = True) -> str:
    """Форматирование одного забега для вывода"""
    import json
    source_info = ""
    if race.get('website_url'):
        source_info = f"\n🔗 Сайт: {race['website_url']}"
    if show_protocol and race.get('protocol_url'):
        source_info += f"\n📄 Протокол: {race['protocol_url']}"
    distances_info = ""
    if race.get('distances'):
        try:
            distances = json.loads(race['distances'])
            if distances:
                dist_names = [d.get('name', '') for d in distances if isinstance(d, dict)]
                if dist_names:
                    distances_info = f"\n🏃 Дистанции: {', '.join(dist_names)}"
        except Exception:
            pass
    type_info = f"\n🏷 {_escape_md(race.get('race_type', 'шоссе'))}" if show_type and race.get('race_type') else ""
    return (
        f"🏁 {_escape_md(race['name'])}\n"
        f"📅 {race['date']}\n"
        f"📍 {_escape_md(race['location'] or 'Место уточняется')}\n"
        f"🏢 Организатор: {_escape_md(race['organizer'] or 'Не указан')}"
        f"{type_info}{distances_info}{source_info}\n"
    )


def _build_pagination_kb(prefix: str, offset: int, total: int, limit: int = 10) -> InlineKeyboardMarkup:
    """Кнопки Назад / Далее"""
    buttons = []
    if offset > 0:
        prev_off = max(0, offset - limit)
        buttons.append(InlineKeyboardButton(text="◀ Назад", callback_data=f"{prefix}:{prev_off}"))
    if total > offset + limit:
        next_off = offset + limit
        buttons.append(InlineKeyboardButton(text="Далее ▶", callback_data=f"{prefix}:{next_off}"))
    page = (offset // limit) + 1
    total_pages = (total + limit - 1) // limit
    if buttons:
        return InlineKeyboardMarkup(inline_keyboard=[[*buttons]])
    return None


def _format_race_footer() -> str:
    """Подсказка под списком забегов"""
    return "\n_Чтобы добавить результат: 🔎 Найти результат → введи ФИО → «Это я»_"


async def _send_calendar_page(bot_or_message, races: list, total: int, offset: int, title: str, prefix: str = "cal"):
    """Отправить страницу календаря с пагинацией. bot_or_message: Message (имеет .chat.id и .answer) или (chat_id, bot)."""
    if hasattr(bot_or_message, "answer"):
        chat_id = bot_or_message.chat.id
        bot = bot_or_message.bot
    else:
        chat_id, bot = bot_or_message
    response = f"{title}\n\n"
    for r in races:
        response += _format_race(r, show_type=True)
        response += "\n"
    response += _format_race_footer()
    kb = _build_pagination_kb(prefix, offset, total)
    await bot.send_message(chat_id, response, reply_markup=kb)


@router.message(F.text == "📅 Календарь")
@router.message(Command("calendar"))
async def cmd_calendar(message: types.Message):
    """Календарь предстоящих забегов с пагинацией"""
    try:
        races, total = await db.get_races_filtered(upcoming_only=True, limit=10, offset=0)
        if not races:
            await message.answer(
                "📅 Календарь забегов скоро появится!\n\n"
                "Мы собираем информацию о предстоящих стартах.\n\n"
                "Поиск: /search город Москва\n"
                "История: /history"
            )
            return
        await _send_calendar_page(
            message, races, total, 0,
            "📅 Предстоящие забеги:"
        )
    except Exception as e:
        import logging
        logging.exception("Ошибка в календаре")
        await message.answer(f"⚠️ Ошибка: {e}")


@router.callback_query(F.data.startswith("cal:"))
async def cb_calendar_page(callback: CallbackQuery):
    """Пагинация календаря"""
    try:
        offset = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer()
        return
    races, total = await db.get_races_filtered(upcoming_only=True, limit=10, offset=offset)
    if not races:
        await callback.answer("Больше забегов нет")
        return
    response = "📅 **Предстоящие забеги:**\n\n"
    for r in races:
        response += _format_race(r, show_type=True)
        response += "\n"
    response += _format_race_footer()
    kb = _build_pagination_kb("cal", offset, total)
    await callback.message.edit_text(response, reply_markup=kb)
    await callback.answer()


# ============================================
# /search - Поиск забегов (дата, город, тип, дистанция)
# ============================================
def _parse_search_args(text: str) -> dict:
    """Парсинг: /search город Москва дата 2026-05 тип трейл 10км | или /search Москва"""
    import re
    from calendar import monthrange
    t = text.strip()
    filters = {}
    # Тип: шоссе, трейл, кросс
    for tt in ("шоссе", "трейл", "кросс", "стадион", "триатлон"):
        if tt in t.lower():
            filters["race_type"] = tt
            break
    # Дата: 2026-05, 01.05.2026, 2026
    m = re.search(r"(\d{4})-(\d{2})", t)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        filters["date_from"] = f"{y}-{mo:02d}-01"
        last = monthrange(y, mo)[1]
        filters["date_to"] = f"{y}-{mo:02d}-{last}"
    else:
        m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", t)
        if m:
            d, mo, y = m.group(1), m.group(2), m.group(3)
            filters["date_from"] = f"{y}-{mo}-{d}"
            filters["date_to"] = filters["date_from"]
        else:
            m = re.search(r"\b(202[4-9]|2030)\b", t)
            if m:
                y = m.group(1)
                filters["date_from"] = f"{y}-01-01"
                filters["date_to"] = f"{y}-12-31"
    # Дистанция: 10км, 21.1, дистанция 10
    m = re.search(r"(?:дистанция|dist)?\s*(\d+(?:\.\d+)?)\s*км|(\d+(?:\.\d+)?)\s*км|дистанция\s*(\d+(?:\.\d+)?)", t, re.I)
    if m:
        filters["distance"] = (m.group(1) or m.group(2) or m.group(3) or "")
    # Город: явно "город X", или city, или одно слово из списка городов
    m = re.search(r"город\s+([^\s\d]+(?:\s+[^\s\d]+)?)|city\s+(\w+)", t, re.I)
    if m:
        filters["city"] = (m.group(1) or m.group(2) or "").strip()
    elif not filters.get("city") and t:
        # Одно слово — может быть город
        words = t.split()
        if len(words) == 1:
            w = words[0]
            for c in CITIES:
                if c.lower() == w.lower() or w.lower() in c.lower():
                    filters["city"] = w
                    break
        if "city" not in filters:
            filters["query"] = t  # название, организатор, место
    return filters


@router.message(Command("search"))
@router.message(F.text == "🔍 Поиск")
async def cmd_search(message: types.Message, state: FSMContext):
    """
    Поиск забегов. Кнопка — запрос критериев; /search Москва — сразу поиск
    """
    # /search с аргументами — сразу ищем
    args = ""
    if message.text and message.text.strip().startswith("/search "):
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else ""
    # Кнопка "🔍 Поиск" — запрашиваем критерии
    if not args:
        await state.set_state(SearchInput.waiting_for_query)
        await message.answer(
            "🔍 **Поиск забегов**\n\n"
            "Напиши город, дату, тип или название:\n"
            "• Москва, Сочи, Казань\n"
            "• 2026-05, 01.05.2026\n"
            "• трейл, шоссе, кросс\n"
            "• 10км, 21.1\n\n"
            "Или /cancel для отмены"
        )
        return
    filters = _parse_search_args(args)
    await _run_search(message, filters, state)


async def _run_search(message, filters: dict, state: FSMContext | None = None):
    """Выполнить поиск и отправить результат"""
    if state:
        await state.clear()
    _last_search[message.from_user.id] = filters
    try:
        races, total = await db.get_races_filtered(
            city=filters.get("city"),
            race_type=filters.get("race_type"),
            date_from=filters.get("date_from"),
            date_to=filters.get("date_to"),
            distance=filters.get("distance"),
            query=filters.get("query"),
            upcoming_only=True,
            limit=10,
            offset=0,
        )
        if not races:
            await message.answer(
                "📭 По твоим критериям забегов не найдено.\n\n"
                "Попробуй: Москва, 2026-05, трейл, 10км"
            )
            return
        title = "🔍 **Результаты поиска:**"
        if filters:
            parts = [f"{k}={v}" for k, v in filters.items()]
            title += f"\n_Фильтры: {', '.join(parts)}_"
        title += f"\n_Найдено: {total}_\n"
        await _send_calendar_page(message, races, total, 0, title, prefix="sr")
    except Exception as e:
        import logging
        logging.exception("Ошибка поиска")
        await message.answer(f"⚠️ Ошибка: {e}")


@router.message(SearchInput.waiting_for_query, Command("cancel"))
@router.message(SearchInput.waiting_for_query, F.text == "❌ Отмена")
async def cancel_search(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ Поиск отменён.")


@router.message(SearchInput.waiting_for_query, F.text)
async def process_search_input(message: types.Message, state: FSMContext):
    """Обработка введённых критериев поиска"""
    text = message.text.strip()
    if len(text) < 2:
        await message.answer("⚠️ Введи минимум 2 символа (город, дата, тип).")
        return
    filters = _parse_search_args(text)
    await _run_search(message, filters, state)


@router.callback_query(F.data.startswith("sr:"))
async def cb_search_page(callback: CallbackQuery):
    """Пагинация результатов поиска"""
    try:
        offset = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer()
        return
    filters = _last_search.get(callback.from_user.id, {})
    races, total = await db.get_races_filtered(
        city=filters.get("city"),
        race_type=filters.get("race_type"),
        date_from=filters.get("date_from"),
        date_to=filters.get("date_to"),
        distance=filters.get("distance"),
        query=filters.get("query"),
        upcoming_only=True,
        limit=10,
        offset=offset,
    )
    if not races:
        await callback.answer("Больше результатов нет")
        return
    response = "🔍 **Результаты поиска:**\n"
    if filters:
        response += f"_Фильтры: {', '.join(f'{k}={v}' for k, v in filters.items())}_\n"
    response += f"_Найдено: {total}_\n\n"
    for r in races:
        response += _format_race(r, show_type=True)
        response += "\n"
    response += _format_race_footer()
    kb = _build_pagination_kb("sr", offset, total)
    await callback.message.edit_text(response, reply_markup=kb)
    await callback.answer()


# ============================================
# КОМАНДА /history - История забегов (с пагинацией и поиском)
# ============================================
@router.message(Command("history"))
@router.message(F.text == "📜 История")
async def cmd_history(message: types.Message):
    """
    История прошедших забегов с пагинацией и поиском.
    /history [город] [дата] [тип] [дистанция]
    Примеры: /history Москва, /history дата 2025-01, /history тип трейл
    """
    args = ""
    if message.text and message.text.strip().startswith("/history "):
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else ""
    filters = _parse_search_args(args) if args else {}
    _last_history_search[message.from_user.id] = filters

    races, total = await db.get_races_filtered(
        city=filters.get("city"),
        race_type=filters.get("race_type"),
        date_from=filters.get("date_from"),
        date_to=filters.get("date_to"),
        distance=filters.get("distance"),
        query=filters.get("query"),
        upcoming_only=False,
        limit=10,
        offset=0,
    )

    if not races:
        hint = "Попробуй: /history город Москва | дата 2025-01 | тип трейл | 10км"
        await message.answer(
            f"📜 По твоим критериям прошедших забегов не найдено.\n\n{hint}"
        )
        return

    title = "📜 **Прошедшие забеги:**"
    if filters:
        parts = [f"{k}={v}" for k, v in filters.items()]
        title += f"\n_Фильтры: {', '.join(parts)}_"
    title += f"\n_Найдено: {total}_\n"
    if not filters:
        title += "\n_Поиск: /history город Москва | дата 2025-01 | тип трейл | 10км_\n"
    await _send_calendar_page(
        message, races, total, 0,
        title, prefix="hist"
    )


@router.callback_query(F.data.startswith("hist:"))
async def cb_history_page(callback: CallbackQuery):
    """Пагинация истории забегов"""
    try:
        offset = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer()
        return
    filters = _last_history_search.get(callback.from_user.id, {})
    races, total = await db.get_races_filtered(
        city=filters.get("city"),
        race_type=filters.get("race_type"),
        date_from=filters.get("date_from"),
        date_to=filters.get("date_to"),
        distance=filters.get("distance"),
        query=filters.get("query"),
        upcoming_only=False,
        limit=10,
        offset=offset,
    )
    if not races:
        await callback.answer("Больше забегов нет")
        return
    response = "📜 **Прошедшие забеги:**\n"
    if filters:
        response += f"_Фильтры: {', '.join(f'{k}={v}' for k, v in filters.items())}_\n"
    response += f"_Найдено: {total}_\n\n"
    for r in races:
        response += _format_race(r, show_type=True)
        response += "\n"
    response += _format_race_footer()
    kb = _build_pagination_kb("hist", offset, total)
    await callback.message.edit_text(response, reply_markup=kb)
    await callback.answer()


# ============================================
# КОМАНДА /parse - Парсинг забегов (админ)
# ============================================
@router.message(Command("parse"))
async def cmd_parse(message: types.Message):
    """Ручной запуск парсинга забегов (только для админов)"""
    if message.from_user.id not in ADMINS or ADMINS[0] == 0:
        await message.answer("⚠️ Эта команда доступна только администраторам.")
        return

    await message.answer("🔄 Запускаю парсинг забегов...\n\nЭто может занять несколько минут.")

    try:
        results = await run_parse()
        total = sum(results.values())

        response = "✅ **Парсинг завершён!**\n\n"
        for source, count in results.items():
            response += f"• {source}: {count} забегов\n"
        response += f"\n📊 Всего добавлено: {total}"

        await message.answer(response)
    except Exception as e:
        await message.answer(f"❌ Ошибка парсинга: {e}")


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
        "⚠️ Вы уверены?\n\n"
        "Это действие удалит:\n"
        "• Ваш профиль\n"
        "• Все ваши результаты\n"
        "• Подписки на забеги\n\n"
        "Восстановить данные будет невозможно.\n\n"
        "Нажмите «✅ Удалить» для подтверждения или «❌ Отмена»",
        reply_markup=get_delete_confirmation_keyboard()
    )
    await state.set_state(DeleteConfirm.waiting)


@router.message(StateFilter(DeleteConfirm.waiting), F.text == "✅ Удалить")
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


@router.message(StateFilter(DeleteConfirm.waiting), F.text == "❌ Отмена")
async def cancel_delete(message: types.Message, state: FSMContext):
    """Отмена удаления"""
    await state.clear()
    await message.answer("✅ Удаление отменено. Ваши данные сохранены.")


# ============================================
# АДМИН: Сбор результатов
# ============================================
@router.message(Command("admin_collect"))
async def cmd_admin_collect(message: types.Message):
    """Запуск сбора результатов с протоколов (только для админов)"""
    if message.from_user.id not in ADMINS or ADMINS[0] == 0:
        await message.answer("⚠️ Только для администраторов.")
        return
    await message.answer("🔄 Запускаю сбор результатов с протоколов...")
    try:
        from bot.scripts.collect_results import run_collect
        await run_collect()
        await message.answer("✅ Сбор завершён.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


# ============================================
# АДМИН: Заявки «это я»
# ============================================
@router.message(Command("admin_claims"))
async def cmd_admin_claims(message: types.Message):
    """Список заявок на привязку результата"""
    if message.from_user.id not in ADMINS or ADMINS[0] == 0:
        await message.answer("⚠️ Только для администраторов.")
        return

    claims = await db.get_pending_result_claims(limit=20)
    if not claims:
        await message.answer("Нет заявок на рассмотрении.")
        return

    text = "🔎 **Заявки «это я»:**\n\n"
    buttons = []
    for c in claims:
        text += f"ID {c['id']}: {c['last_name']} {c['first_name']} — {c['race_name']} ({c['distance']})\n"
        text += f"  Время: {c.get('finish_time', '—')}\n\n"
        buttons.append([
            InlineKeyboardButton(text=f"✅ {c['id']}", callback_data=f"acl_ok:{c['id']}"),
            InlineKeyboardButton(text=f"❌ {c['id']}", callback_data=f"acl_no:{c['id']}"),
        ])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(text[:4000], reply_markup=kb)


@router.callback_query(F.data.startswith("acl_ok:"))
async def cb_admin_claim_approve(callback: CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("Нет доступа")
        return
    try:
        claim_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer()
        return
    ok = await db.approve_result_claim(claim_id, callback.from_user.id)
    await callback.answer("Одобрено" if ok else "Ошибка")
    if ok:
        await callback.message.edit_text(callback.message.text + "\n\n✅ Заявка одобрена")


@router.callback_query(F.data.startswith("acl_no:"))
async def cb_admin_claim_reject(callback: CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("Нет доступа")
        return
    try:
        claim_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer()
        return
    ok = await db.reject_result_claim(claim_id, callback.from_user.id)
    await callback.answer("Отклонено" if ok else "Ошибка")
    if ok:
        await callback.message.edit_text(callback.message.text + "\n\n❌ Заявка отклонена")


# ============================================
# АДМИН: Удаление данных о забеге (по запросу организатора)
# ============================================
@router.message(Command("admin_delete_race"))
async def cmd_admin_delete_race(message: types.Message):
    """Удаление данных о забеге по запросу организатора (только для админов)"""
    if message.from_user.id not in ADMINS or ADMINS[0] == 0:
        await message.answer("⚠️ Эта команда доступна только администраторам.")
        return
    
    # Парсинг команды: /admin_delete_race <race_id> или /admin_delete_race organizer <название>
    parts = message.text.split(maxsplit=2)
    
    if len(parts) < 2:
        await message.answer(
            "📋 Удаление данных о забеге\n\n"
            "Использование:\n"
            "• `/admin_delete_race <ID забега>` - удалить конкретный забег\n"
            "• `/admin_delete_race organizer <Название организатора>` - удалить все забеги организатора\n\n"
            "⚠️ Это действие необратимо!"
        )
        return
    
    try:
        if parts[1].lower() == 'organizer' and len(parts) > 2:
            # Удаление всех забегов организатора
            organizer = parts[2]
            stats = await db.delete_races_by_organizer(organizer)
            
            await message.answer(
                f"✅ **Данные удалены**\n\n"
                f"Организатор: {organizer}\n"
                f"Забегов удалено: {stats['races_deleted']}\n"
                f"Результатов удалено: {stats['results_deleted']}\n"
                f"Подписок удалено: {stats['subscriptions_deleted']}\n\n"
                f"Все данные о забегах {organizer} удалены из базы."
            )
        else:
            # Удаление конкретного забега
            race_id = int(parts[1])
            race = await db.get_race_by_id(race_id)
            
            if not race:
                await message.answer(f"⚠️ Забег с ID {race_id} не найден.")
                return
            
            stats = await db.delete_race(race_id)
            
            await message.answer(
                f"✅ **Забег удалён**\n\n"
                f"Название: {race['name']}\n"
                f"Дата: {race['date']}\n"
                f"Организатор: {race.get('organizer', 'Не указан')}\n\n"
                f"Статистика удаления:\n"
                f"• Результатов: {stats['results_deleted']}\n"
                f"• Подписок: {stats['subscriptions_deleted']}\n\n"
                f"Все данные о забеге удалены из базы."
            )
    except ValueError:
        await message.answer("⚠️ Неверный формат команды. Используйте: `/admin_delete_race <ID>` или `/admin_delete_race organizer <Название>`")
    except Exception as e:
        await message.answer(f"❌ Ошибка при удалении: {e}")


# ============================================
# АДМИН: Просмотр обратной связи
# ============================================
@router.message(Command("admin_feedback"))
async def cmd_admin_feedback(message: types.Message):
    """Просмотр последних сообщений обратной связи (только для админов)"""
    if message.from_user.id not in ADMINS or ADMINS[0] == 0:
        await message.answer("⚠️ Эта команда доступна только администраторам.")
        return

    feedback_list = await db.get_feedback_list(limit=15)

    if not feedback_list:
        await message.answer("📭 Пока нет сообщений обратной связи.")
        return

    response = "💬 Последние сообщения обратной связи:\n\n"
    for fb in feedback_list:
        name = f"{fb.get('last_name', '')} {fb.get('first_name', '')}".strip() or "—"
        text_preview = (fb['text'][:100] + "…") if len(fb['text']) > 100 else fb['text']
        response += (
            f"ID {fb['id']} | tg:{fb['telegram_id']} ({name})\n"
            f"{text_preview}\n"
            f"_{fb['created_at']}_\n\n"
        )

    await message.answer(response[:4000])
