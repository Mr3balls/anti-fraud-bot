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

# --- Загружаем статистику ---
try:
    with open("scores.json", "r", encoding="utf-8") as f:
        SCORES = json.load(f)
except FileNotFoundError:
    SCORES = {}

user_state = {}  # Будет хранить {"score": 0, "current": 0, "lang": "ru"}

# --- Сохранение статистики ---
def save_scores():
    with open("scores.json", "w", encoding="utf-8") as f:
        json.dump(SCORES, f, ensure_ascii=False, indent=2)

# --- Уровни и достижения ---
def get_level(points: int):
    if points < 5:
        return "Новичок 🔰"
    elif points < 10:
        return "Бдительный 👀"
    elif points < 20:
        return "Цифровой защитник 🛡️"
    elif points < 30:
        return "Мастер кибербезопасности 🚀"
    else:
        return "Легенда цифровой безопасности 👑"

def get_achievement(points: int):
    if points == 5:
        return "🎖 Достижение: Осторожный пользователь!"
    elif points == 15:
        return "🛡 Достижение: Кибергерой!"
    elif points == 30:
        return "👑 Достижение: Легенда безопасности!"
    return None

# --- Мультиязычные тексты ---
TEXTS = {
    "menu": {
        "ru": ["🎯 Начать викторину", "📚 Режим обучения", "📊 Таблица лидеров", "📈 Моя статистика", "Сайт со статистикой"],
        "en": ["🎯 Quiz", "📚 Learning mode", "📊 Leaderboard", "📈 My stats", "Web panel"],
        "kz": ["🎯 Викторина", "📚 Оқу режимі", "📊 Лидерлер тізімі", "📈 Менің статистикам", "Веб-панель"]
    },
    "start": {
        "ru": "👋 Привет! Выберите язык:",
        "en": "👋 Hello! Choose language:",
        "kz": "👋 Сәлем! Тілді таңдаңыз:"
    },
    "lang_set": {
        "ru": "Язык выбран: Русский",
        "en": "Language set: English",
        "kz": "Тіл таңдалды: Қазақша"
    },
    "quiz_start": {
        "ru": "🧠 Викторина начинается! 5 вопросов, по 30 сек. 🚀",
        "en": "🧠 Quiz starts! 5 questions, 30 sec each 🚀",
        "kz": "🧠 Викторина басталды! 5 сұрақ, әрқайсысы 30 секунд 🚀"
    },
    "web_panel": {
        "ru": f"🌐 Панель статистики доступна здесь:\n{WEB_URL}",
        "en": f"🌐 Web panel available here:\n{WEB_URL}",
        "kz": f"🌐 Статистика панелі осында қолжетімді:\n{WEB_URL}"
    }
}

# --- Главное меню с учетом языка ---
def main_menu(user_id=None):
    lang = user_state.get(user_id, {}).get("lang", "ru")
    kb = ReplyKeyboardBuilder()
    for label in TEXTS["menu"][lang]:
        kb.button(text=label)
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

# --- Выбор языка при старте ---
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.username or str(message.from_user.id)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇷🇺 Русский")],
            [KeyboardButton(text="🇺🇸 English")],
            [KeyboardButton(text="🇰🇿 Қазақша")]
        ],
        resize_keyboard=True
    )
    await message.answer(TEXTS["start"]["ru"], reply_markup=kb)


@dp.message(F.text.in_({"🇷🇺 Русский", "🇺🇸 English", "🇰🇿 Қазақша"}))
async def set_language(message: types.Message):
    user_id = message.from_user.username or str(message.from_user.id)
    lang_map = {"🇷🇺 Русский": "ru", "🇺🇸 English": "en", "🇰🇿 Қазақша": "kz"}
    user_state[user_id] = {"score": 0, "current": 0, "lang": lang_map[message.text]}
    await message.answer(TEXTS["lang_set"][lang_map[message.text]], reply_markup=main_menu(user_id))

# --- Кнопки меню ---
@dp.message(F.text.in_(TEXTS["menu"]["ru"] + TEXTS["menu"]["en"] + TEXTS["menu"]["kz"]))
async def menu_handler(message: types.Message):
    user_id = message.from_user.username or str(message.from_user.id)
    lang = user_state.get(user_id, {}).get("lang", "ru")
    text = message.text

    if text == TEXTS["menu"][lang][0]:  # Викторина
        await start_quiz(message)
    elif text == TEXTS["menu"][lang][1]:  # Режим обучения
        await learn_mode(message)
    elif text == TEXTS["menu"][lang][2]:  # Таблица лидеров
        await leaderboard(message)
    elif text == TEXTS["menu"][lang][3]:  # Моя статистика
        await stats(message)
    elif text == TEXTS["menu"][lang][4]:  # Сайт
        await web_panel(message)

# --- Викторина ---
async def start_quiz(message: types.Message):
    user_id = message.from_user.username or str(message.from_user.id)
    lang = user_state[user_id]["lang"]
    user_state[user_id]["score"] = 0
    user_state[user_id]["current"] = 0
    await message.answer(TEXTS["quiz_start"][lang])
    await send_question(message)

async def send_question(message: types.Message):
    user_id = message.from_user.username or str(message.from_user.id)
    state = user_state[user_id]
    lang = state.get("lang", "ru")
    current_q = state["current"]

    if current_q >= 5:
        total_score = state["score"]
        SCORES[user_id] = SCORES.get(user_id, 0) + total_score
        save_scores()
        text = f"🏁 Викторина завершена!\nОчки: {total_score}\nВсего: {SCORES[user_id]}\nУровень: {get_level(SCORES[user_id])}"
        await message.answer(text, reply_markup=main_menu(user_id))
        user_state.pop(user_id, None)
        return

    question = random.choice(QUESTIONS)
    state["question"] = question["id"]
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=opt["text"][lang])] for opt in question["options"]],
        resize_keyboard=True
    )
    await message.answer(f"❓ Вопрос {current_q + 1}/5:\n\n⚠️ {question['situation'][lang]}", reply_markup=markup)

@dp.message(F.text)
async def check_answer(message: types.Message):
    if message.text.startswith("/"):
        return
    user_id = message.from_user.username or str(message.from_user.id)
    if user_id not in user_state:
        return
    state = user_state[user_id]
    lang = state.get("lang", "ru")
    question_id = state.get("question")
    question = next((q for q in QUESTIONS if q["id"] == question_id), None)
    if not question:
        return

    for opt in question["options"]:
        if message.text == opt["text"][lang]:
            if opt["isCorrect"]:
                state["score"] += 1
                await message.answer(f"✅ Правильно!\n💡 {opt['feedback'][lang]}")
            else:
                await message.answer(f"❌ Неверно.\n💡 {opt['feedback'][lang]}")
            break

    state["current"] += 1
    await asyncio.sleep(1)
    await send_question(message)

# --- Остальные функции ---
async def learn_mode(message: types.Message):
    user_id = message.from_user.username or str(message.from_user.id)
    lang = user_state[user_id]["lang"]
    tip = random.choice(QUESTIONS)
    feedbacks = "\n\n".join([f"💡 {opt['feedback'][lang]}" for opt in tip["options"]])
    await message.answer(f"📖 Режим обучения:\n\n⚠️ {tip['situation'][lang]}\n\n{feedbacks}")

async def leaderboard(message: types.Message):
    if not SCORES:
        await message.answer("Пока никто не играл 😅")
        return
    top = sorted(SCORES.items(), key=lambda x: x[1], reverse=True)[:5]
    text = "🏆 Топ игроков:\n\n"
    for i, (uid, score) in enumerate(top, 1):
        name = f"@{uid}" if not uid.isdigit() else f"ID {uid[-5:]}"
        text += f"{i}. {name} — {score} очков ({get_level(score)})\n"
    await message.answer(text)

async def stats(message: types.Message):
    user_id = message.from_user.username or str(message.from_user.id)
    points = SCORES.get(user_id, 0)
    await message.answer(f"📊 Очков: {points}\nУровень: {get_level(points)}")

async def web_panel(message: types.Message):
    await message.answer(TEXTS["web_panel"]["ru"])

# --- Для web.py ---
def get_dispatcher():
    return dp, bot, SCORES, save_scores, get_level, get_achievement, user_state, QUESTIONS, WEB_URL
