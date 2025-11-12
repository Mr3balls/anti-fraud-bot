import os
import asyncio
from aiohttp import web

# --- Импортируем бот и все функции ---
from bot import get_dispatcher
import bot  # гарантирует регистрацию всех хэндлеров

dp, bot_instance, SCORES, save_scores, get_level, get_achievement, user_state, QUESTIONS = get_dispatcher()

async def web_handler(request):
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    rows = "\n".join([
        f"<tr><td>{uid}</td><td>{score}</td><td>{get_level(score)}</td></tr>"
        for uid, score in sorted(SCORES.items(), key=lambda x: x[1], reverse=True)
    ])
    html = html.replace("{{rows}}", rows)
    return web.Response(text=html, content_type="text/html")

async def run_web():
    app = web.Application()
    app.router.add_get("/", web_handler)
    port = int(os.getenv("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Веб-панель доступна на порту {port}")

async def main():
    print("🚀 Бот и веб-сервер запущены!")
    # запускаем веб-сервер как основной процесс, а бота — как фоновую задачу
    asyncio.create_task(dp.start_polling(bot_instance))
    await run_web()

if __name__ == "__main__":
    asyncio.run(main())
