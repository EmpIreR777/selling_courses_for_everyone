import asyncio
from aiogram.types import BotCommand, BotCommandScopeDefault
from loguru import logger
from bot.config import bot, admin, dp
from bot.dao.database_middleware import DatabaseMiddlewareWithoutCommit, DatabaseMiddlewareWithCommit
from bot.admin.admin import admin_router
from bot.user.user_router import user_router
from bot.user.catalog_router import catalog_router


# Функция, которая настроит командное меню (дефолтное для всех пользователей)
async def set_commands():
    commands = [BotCommand(command='start', description='Старт')]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


# Функция, которая выполнится когда бот запустится
async def start_bot():
    await set_commands()
    try:
        await bot.send_message(admin, f'Я запущен🥳.')
    except:
        pass
    logger.info('Бот успешно запущен.')


# Функция, которая выполнится когда бот завершит свою работу
async def stop_bot():
    try:
        for admin_id in admin:
            await bot.send_message(admin_id, 'Бот остановлен. За что?😔')
    except:
        pass
    logger.error('Бот остановлен!')


async def main():
    # регистрация мидлварей
    dp.update.middleware.register(DatabaseMiddlewareWithoutCommit())
    dp.update.middleware.register(DatabaseMiddlewareWithCommit())

    # регистрация роутеров
    dp.include_router(catalog_router)
    dp.include_router(user_router)
    dp.include_router(admin_router)

    # регистрация функций
    dp.startup.register(start_bot)
    dp.shutdown.register(stop_bot)

    # запуск бота в режиме long polling при запуске бот очищает все обновления, которые были за его моменты бездействия
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())