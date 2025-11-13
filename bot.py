from dotenv import load_dotenv
import json
import random
import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, ReplyKeyboardMarkup, KeyboardButton

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
WEB_URL = "https://web-production-695f2.up.railway.app"
if not WEB_URL:
    raise RuntimeError("❌ WEB_URL не задана!")

# --- Загружаем вопросы ---
with open("questions.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

# --- Загружаем переводы ---
LOCALES = {}
for lang in ['ru', 'kz', 'en']:
    try:
        with open(f"locales/{lang}.json", "r", encoding="utf-8") as f:
            LOCALES[lang] = json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Файл перевода {lang}.json не найден")

# --- Загружаем обучающие примеры ---
LEARNING_EXAMPLES = {}
for lang in ['ru', 'kz', 'en']:
    try:
        with open(f"learning_examples/{lang}.json", "r", encoding="utf-8") as f:
            LEARNING_EXAMPLES[lang] = json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Файл обучающих примеров {lang}.json не найден")
        LEARNING_EXAMPLES[lang] = {"examples": []}

# --- Загружаем статистику и настройки языка ---
try:
    with open("scores.json", "r", encoding="utf-8") as f:
        SCORES = json.load(f)
except FileNotFoundError:
    SCORES = {}

try:
    with open("user_languages.json", "r", encoding="utf-8") as f:
        USER_LANGUAGES = json.load(f)
except FileNotFoundError:
    USER_LANGUAGES = {}

user_state = {}

# --- Сохранение статистики ---
def save_scores():
    with open("scores.json", "w", encoding="utf-8") as f:
        json.dump(SCORES, f, ensure_ascii=False, indent=2)

# --- Сохранение языковых настроек ---
def save_languages():
    with open("user_languages.json", "w", encoding="utf-8") as f:
        json.dump(USER_LANGUAGES, f, ensure_ascii=False, indent=2)

# --- Получение перевода ---
def get_text(user_id, key, **kwargs):
    lang = USER_LANGUAGES.get(str(user_id), 'ru')
    text = LOCALES[lang].get(key, LOCALES['ru'].get(key, key))
    
    # Заменяем переменные в тексте
    for k, v in kwargs.items():
        text = text.replace(f"{{{k}}}", str(v))
    
    return text

# --- Получение обучающего примера ---
def get_learning_example(user_id):
    lang = USER_LANGUAGES.get(str(user_id), 'ru')
    examples = LEARNING_EXAMPLES[lang]["examples"]
    if not examples:
        # Если нет примеров на выбранном языке, используем русский
        examples = LEARNING_EXAMPLES['ru']["examples"]
    return random.choice(examples)

# --- Уровни и достижения ---
def get_level(points: int, user_id):
    if points < 5:
        return get_text(user_id, "levels.0")
    elif points < 10:
        return get_text(user_id, "levels.5")
    elif points < 20:
        return get_text(user_id, "levels.10")
    elif points < 30:
        return get_text(user_id, "levels.20")
    else:
        return get_text(user_id, "levels.30")

def get_achievement(points: int, user_id):
    if points == 5:
        return get_text(user_id, "achievements.5")
    elif points == 15:
        return get_text(user_id, "achievements.15")
    elif points == 30:
        return get_text(user_id, "achievements.30")
    return None

# --- Главное меню ---
def main_menu(user_id):
    kb = ReplyKeyboardBuilder()
    kb.button(text=get_text(user_id, "menu_start_quiz"))
    kb.button(text=get_text(user_id, "menu_learn"))
    kb.button(text=get_text(user_id, "menu_leaderboard"))
    kb.button(text=get_text(user_id, "menu_stats"))
    kb.button(text=get_text(user_id, "menu_website"))
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

# --- Меню выбора языка ---
def language_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🇷🇺 Русский")
    kb.button(text="🇰🇿 Қазақша") 
    kb.button(text="🇺🇸 English")
    kb.adjust(3)
    return kb.as_markup(resize_keyboard=True)

# --- Команды ---
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    
    # Если язык еще не выбран, предлагаем выбрать
    if user_id not in USER_LANGUAGES:
        await message.answer(
            get_text(user_id, "choose_language"),
            reply_markup=language_menu()
        )
        return
    
    await message.answer(
        get_text(user_id, "start"),
        reply_markup=main_menu(user_id)
    )

@dp.message(Command("lang"))
async def change_language(message: types.Message):
    user_id = str(message.from_user.id)
    await message.answer(
        get_text(user_id, "choose_language"),
        reply_markup=language_menu()
    )

@dp.message(F.text.in_(["🇷🇺 Русский", "🇰🇿 Қазақша", "🇺🇸 English"]))
async def set_language(message: types.Message):
    user_id = str(message.from_user.id)
    
    if message.text == "🇷🇺 Русский":
        USER_LANGUAGES[user_id] = 'ru'
        lang_text = get_text(user_id, "language_set")
    elif message.text == "🇰🇿 Қазақша":
        USER_LANGUAGES[user_id] = 'kz'
        lang_text = get_text(user_id, "language_set")
    else:  # English
        USER_LANGUAGES[user_id] = 'en'
        lang_text = get_text(user_id, "language_set")
    
    save_languages()
    await message.answer(lang_text, reply_markup=main_menu(user_id))

@dp.message(Command("help"))
async def help_command(message: types.Message):
    user_id = str(message.from_user.id)
    await message.answer(get_text(user_id, "help"))

@dp.message(Command("learn"))
async def learn_command(message: types.Message):
    user_id = str(message.from_user.id)
    example = get_learning_example(user_id)
    
    # Форматируем советы в виде списка
    tips_text = "\n".join([f"• {tip}" for tip in example["tips"]])
    
    response_text = (
        f"{get_text(user_id, 'learn_example')}\n\n"
        f"⚠️ {example['situation']}\n\n"
        f"🔍 {example['explanation']}\n\n"
        f"💡 **Советы для безопасности:**\n"
        f"{tips_text}"
    )
    
    await message.answer(response_text)

@dp.message(Command("leaderboard"))
async def leaderboard_command(message: types.Message):
    user_id = str(message.from_user.id)
    if not SCORES:
        await message.answer(get_text(user_id, "leaderboard_empty"))
        return
    
    top = sorted(SCORES.items(), key=lambda x: x[1], reverse=True)[:5]
    text = get_text(user_id, "leaderboard_title")
    for i, (uid, score) in enumerate(top, 1):
        name = f"@{uid}" if not uid.isdigit() else f"ID {uid[-5:]}"
        text += f"{i}. {name} — {score} {get_text(user_id, 'points')} ({get_level(score, user_id)})\n"
    await message.answer(text)

@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    user_id = str(message.from_user.id)
    user_key = message.from_user.username or str(message.from_user.id)
    points = SCORES.get(user_key, 0)
    await message.answer(get_text(user_id, "stats_text", points=points, level=get_level(points, user_id)))

@dp.message(Command("web"))
async def web_command(message: types.Message):
    user_id = str(message.from_user.id)
    await message.answer(get_text(user_id, "web_panel", url=WEB_URL))

@dp.message(Command("quiz"))
async def quiz_command(message: types.Message):
    await start_quiz(message)

@dp.message(F.text)
async def handle_text(message: types.Message):
    user_id = str(message.from_user.id)
    user_text = message.text
    
    # Обработка кнопок главного меню
    if user_text == get_text(user_id, "menu_learn"):
        example = get_learning_example(user_id)
        
        # Форматируем советы в виде списка
        tips_text = "\n".join([f"• {tip}" for tip in example["tips"]])
        
        response_text = (
            f"{get_text(user_id, 'learn_example')}\n\n"
            f"⚠️ {example['situation']}\n\n"
            f"🔍 {example['explanation']}\n\n"
            f"💡 **Советы для безопасности:**\n"
            f"{tips_text}"
        )
        
        await message.answer(response_text)
    
    elif user_text == get_text(user_id, "menu_leaderboard"):
        if not SCORES:
            await message.answer(get_text(user_id, "leaderboard_empty"))
            return
        
        top = sorted(SCORES.items(), key=lambda x: x[1], reverse=True)[:5]
        text = get_text(user_id, "leaderboard_title")
        for i, (uid, score) in enumerate(top, 1):
            name = f"@{uid}" if not uid.isdigit() else f"ID {uid[-5:]}"
            text += f"{i}. {name} — {score} {get_text(user_id, 'points')} ({get_level(score, user_id)})\n"
        await message.answer(text)
    
    elif user_text == get_text(user_id, "menu_stats"):
        user_key = message.from_user.username or str(message.from_user.id)
        points = SCORES.get(user_key, 0)
        await message.answer(get_text(user_id, "stats_text", points=points, level=get_level(points, user_id)))
    
    elif user_text == get_text(user_id, "menu_website"):
        await message.answer(get_text(user_id, "web_panel", url=WEB_URL))
    
    elif user_text == get_text(user_id, "menu_start_quiz"):
        await start_quiz(message)
    
    else:
        # Обработка ответов в викторине
        await check_answer(message)

async def start_quiz(message: types.Message):
    user_id = str(message.from_user.id)
    user_key = message.from_user.username or str(message.from_user.id)
    user_state[user_key] = {"score": 0, "current": 0}
    await message.answer(get_text(user_id, "quiz_start"))
    await send_question(message)

async def send_question(message: types.Message):
    user_id = str(message.from_user.id)
    user_key = message.from_user.username or str(message.from_user.id)
    state = user_state[user_key]
    current_q = state["current"]

    if current_q >= 5:
        total_score = state["score"]
        SCORES[user_key] = SCORES.get(user_key, 0) + total_score
        save_scores()
        achievement = get_achievement(SCORES[user_key], user_id)
        
        text = get_text(user_id, "quiz_complete", 
                       score=total_score, 
                       total=SCORES[user_key], 
                       level=get_level(SCORES[user_key], user_id))
        
        if achievement:
            text += f"\n\n{achievement}"
        await message.answer(text, reply_markup=main_menu(user_id))
        user_state.pop(user_key, None)
        return

    question = random.choice(QUESTIONS)
    state["question"] = question["id"]
    
    # Получаем язык пользователя
    lang = USER_LANGUAGES.get(str(user_id), 'ru')
    
    # Создаем клавиатуру с вариантами на нужном языке
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=opt["text"][lang])] for opt in question["options"]],
        resize_keyboard=True
    )
    
    await message.answer(
        get_text(user_id, "quiz_question", current=current_q + 1, situation=question['situation'][lang]),
        reply_markup=markup
    )

async def check_answer(message: types.Message):
    # Игнорируем команды и выбор языка
    if (message.text.startswith("/") or 
        message.text in ["🇷🇺 Русский", "🇰🇿 Қазақша", "🇺🇸 English"]):
        return

    user_id = str(message.from_user.id)
    user_key = message.from_user.username or str(message.from_user.id)
    
    # Проверяем, что пользователь в состоянии викторины
    if user_key not in user_state:
        return

    state = user_state[user_key]
    question_id = state.get("question")
    question = next((q for q in QUESTIONS if q["id"] == question_id), None)
    if not question:
        return

    # Получаем язык пользователя
    lang = USER_LANGUAGES.get(str(user_id), 'ru')

    for opt in question["options"]:
        if message.text == opt["text"][lang]:
            if opt["isCorrect"]:
                state["score"] += 1
                await message.answer(get_text(user_id, "quiz_correct", feedback=opt['feedback'][lang]))
            else:
                await message.answer(get_text(user_id, "quiz_incorrect", feedback=opt['feedback'][lang]))
            break

    state["current"] += 1
    await asyncio.sleep(1)
    await send_question(message)

# --- Для web.py ---
def get_dispatcher():
    return dp, bot, SCORES, save_scores, get_level, get_achievement, user_state, QUESTIONS, WEB_URL, USER_LANGUAGES, LOCALES