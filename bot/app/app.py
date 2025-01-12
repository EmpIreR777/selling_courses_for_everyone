import datetime
from aiohttp import web
from aiogram.types import Update
from loguru import logger

from bot.config import bot, dp, settings


async def handle_webhook(request: web.Request):
    try:
        update = Update(**await request.json())
        await dp.feed_update(bot, update)
        return web.Response(status=200)
    except Exception as e:
        logger.error(f'Ошибка при обработке вебхука: {e}')
        return web.Response(status=500)


# Функция для обработки запроса на эндпоинт главной страницы веб-сервера
async def home_page(request: web.Request) -> web.Response:
    """
    Обработчик для отображения главной страницы с информацией о сервисе.
    """
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>aiohttp Демонстрация</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; }}
            h1 {{ color: #333; }}
            .info {{ background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <h1>Привет, это демонстрация Aiohttp</h1>
        <p>Этот сервер обрабатывает:</p>
        <ul>
            <li>Хуки от Telegram-бота</li>
            <li>Хуки от RoboKassa</li>
        </ul>
        <p>Текущее время сервера: {current_time}</p>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')

