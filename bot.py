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

# --- Загружаем вопросы ---
with open("questions.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

# --- Загружаем статистику ---
try:
    with open("scores.json", "r", encoding="utf-8") as f:
        SCORES = json.load(f)
except FileNotFoundError:
    SCORES = {}

user_state = {}

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

# --- Главное меню ---
def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🎯 Начать викторину")
    kb.button(text="📚 Режим обучения")
    kb.button(text="📊 Таблица лидеров")
    kb.button(text="📈 Моя статистика")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

# --- Команды ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 Привет! Я тренажёр «Анти-мошенник».\n\n"
        "🎯 Помогу тебе распознавать онлайн-мошенничество.\n"
        "Выбери действие или введи команду /help.",
        reply_markup=main_menu()
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "📜 Доступные команды:\n\n"
        "/start — начать\n"
        "/quiz — пройти викторину\n"
        "/learn — обучение\n"
        "/leaderboard — лидеры\n"
        "/stats — статистика\n"
        "/web — ссылка на веб-панель"
    )

@dp.message(Command("learn"))
@dp.message(F.text == "📚 Режим обучения")
async def learn(message: types.Message):
    tip = random.choice(QUESTIONS)
    feedbacks = "\n\n".join([f"💡 {opt['feedback']}" for opt in tip["options"]])
    await message.answer(f"📖 Обучающий пример:\n\n⚠️ {tip['situation']}\n\n{feedbacks}")

@dp.message(Command("leaderboard"))
@dp.message(F.text == "📊 Таблица лидеров")
async def leaderboard(message: types.Message):
    if not SCORES:
        await message.answer("Пока никто не играл 😅")
        return
    top = sorted(SCORES.items(), key=lambda x: x[1], reverse=True)[:5]
    text = "🏆 Топ игроков:\n\n"
    for i, (uid, score) in enumerate(top, 1):
        text += f"{i}. ID {uid[-5:]} — {score} очков ({get_level(score)})\n"
    await message.answer(text)

@dp.message(Command("stats"))
@dp.message(F.text == "📈 Моя статистика")
async def stats(message: types.Message):
    user_id = str(message.from_user.id)
    points = SCORES.get(user_id, 0)
    await message.answer(f"📊 Очков: {points}\nУровень: {get_level(points)}")

@dp.message(Command("quiz"))
@dp.message(F.text == "🎯 Начать викторину")
async def quiz(message: types.Message):
    user_id = str(message.from_user.id)
    user_state[user_id] = {"score": 0, "current": 0}
    await message.answer("🧠 Викторина начинается! 5 вопросов, по 30 сек. 🚀")
    await send_question(message)

async def send_question(message: types.Message):
    user_id = str(message.from_user.id)
    state = user_state[user_id]
    current_q = state["current"]

    if current_q >= 5:
        total_score = state["score"]
        SCORES[user_id] = SCORES.get(user_id, 0) + total_score
        save_scores()
        achievement = get_achievement(SCORES[user_id])
        text = (
            f"🏁 Викторина завершена!\n"
            f"Очки: {total_score}\n"
            f"Всего: {SCORES[user_id]}\n"
            f"Уровень: {get_level(SCORES[user_id])}"
        )
        if achievement:
            text += f"\n\n{achievement}"
        await message.answer(text, reply_markup=main_menu())
        user_state.pop(user_id, None)
        return

    question = random.choice(QUESTIONS)
    state["question"] = question["id"]
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=opt["text"])] for opt in question["options"]],
        resize_keyboard=True
    )
    await message.answer(f"❓ Вопрос {current_q + 1}/5:\n\n⚠️ {question['situation']}", reply_markup=markup)

async def wait_for_answer(message):
    await asyncio.sleep(10)

@dp.message(F.text)
async def check_answer(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in user_state:
        return
    state = user_state[user_id]
    question_id = state.get("question")
    question = next((q for q in QUESTIONS if q["id"] == question_id), None)
    if not question:
        return

    for opt in question["options"]:
        if message.text == opt["text"]:
            if opt["isCorrect"]:
                state["score"] += 1
                await message.answer(f"✅ Правильно!\n💡 {opt['feedback']}")
            else:
                await message.answer(f"❌ Неверно.\n💡 {opt['feedback']}")
            break

    state["current"] += 1
    await asyncio.sleep(1)
    await send_question(message)

@dp.message(Command("web"))
async def web_link(message: types.Message):
    web_url = os.getenv("WEB_URL", "https://example.com")
    print("WEB command triggered!")  # для проверки в логах
    await message.answer(f"🌐 Панель статистики доступна здесь:\n{web_url}")

# --- Для web.py ---
def get_dispatcher():
    return dp, bot, SCORES, save_scores, get_level, get_achievement, user_state, QUESTIONS
