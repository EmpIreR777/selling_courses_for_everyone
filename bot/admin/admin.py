import asyncio
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings, bot
from bot.dao.dao import UserDAO, ProductDao, PurchaseDao, CategoryDao
from bot.admin.kbs import (admin_kb, admin_kb_back, product_management_kb,
                        cancel_kb_inline, catalog_admin_kb,
                        admin_send_file_kb, admin_confirm_kb, dell_product_kb)
from bot.admin.schemas import ProductIDModel, ProductModel
from bot.admin.utils import process_dell_next_msg


admin_router = Router()


class AddProduct(StatesGroup):
    name = State()
    description = State()
    price = State()
    file_id = State()
    category_id = State()
    hidden_content = State()
    confirm_add = State()


@admin_router.callback_query(
        F.data == 'admin_panel', F.from_user.id == settings.ADMIN_ID)
async def start_admin(call: CallbackQuery):
    await call.answer('Доступ в админ-панель разрешён!')
    await call.message.edit_text(
        text='Вам разрешён доступ в админ-панель. Выберите необходимые действие.',
        reply_markup=admin_kb()
    )


@admin_router.callback_query(F.data == 'statistic', F.from_user.id == settings.ADMIN_ID)
async def admin_statistic(call: CallbackQuery, session_without_commit: AsyncSession):
    await call.answer('Запрос не получение статистики...')
    await call.answer('📊 Собираем статистику...')
    stats = await UserDAO.get_statistics(session=session_without_commit)
    total_sum = await PurchaseDao.get_full_sum(session=session_without_commit)
    stats_message = (
        '📈 Статистика пользователей:\n\n'
        f'👥 Всего пользователей: {stats['total_users']}\n'
        f'🆕 Новых за сегодня: {stats['new_today']}\n'
        f'📅 Новых за неделю: {stats['new_week']}\n'
        f'📆 Новых за месяц: {stats['new_month']}\n\n'
        f'💰 Общая сумма заказов: {total_sum} руб.\n\n'
        '🕒 Данные актуальны на текущий момент.'
    )
    await call.message.edit_text(
        text=stats_message, reply_markup=admin_kb()
    )


@admin_router.callback_query(
    F.data == 'process_products', F.from_user.id == settings.ADMIN_ID)
async def admin_process_products(
    call: CallbackQuery, session_without_commit: AsyncSession):
    await call.answer('Режим управления товарами')
    all_products_count = await ProductDao.count(session=session_without_commit)
    await call.message.edit_text(
        text=f'На данный момент в базе данных {all_products_count} товаров. Что будем делать?',
        reply_markup=product_management_kb()
    )


@admin_router.callback_query(
    F.data == 'delete_product', F.from_user.id == settings.ADMIN_ID)
async def admin_process_start_dell(
    call: CallbackQuery, session_without_commit: AsyncSession):
    await call.answer('Режим удаления товаров')
    all_products = await ProductDao.find_all(session=session_without_commit)
    await call.message.edit_text(
        text=f'На данный момент в базе данных {len(all_products)} товаров. Для удаления нажмине на кнопку ниже'
    )
    for product_data in all_products:
        file_id = product_data.file_id
        file_text = '📦 Товар с файлом' if file_id else '📄 Товар без файла'
    product_text = (f'🛒 Описание товара:\n\n'
                    f'🔹 <b>Название товара:</b> <b>{product_data.name}</b>\n'
                    f'🔹 <b>Описание:</b>\n\n<b>{product_data.description}</b>\n\n'
                    f'🔹 <b>Цена:</b> <b>{product_data.price} ₽</b>\n'
                    f'🔹 <b>Описание (закрытое):</b>\n\n<b>{product_data.hidden_content}</b>\n\n'
                    f'<b>{file_text}</b>')
    if file_id:
        await call.message.answer_document(
            document=file_id, caption=product_text,
            reply_markup=dell_product_kb(product_data.id)
            )
    else:
        await call.message.answer(
            text=product_text, reply_markup=dell_product_kb(product_data.id)
        )

@admin_router.callback_query(
    F.data.startswith('dell_'), F.from_user.id == settings.ADMIN_ID)
async def admin_process_start_dell(
    call: CallbackQuery, session_with_commit: AsyncSession):
    product_id = int(call.data.split('_')[-1])
    await ProductDao.delete(session=session_with_commit,
                             filters=ProductIDModel(id=product_id))
    await call.answer(f'Товар по ID {product_id} удален!', show_alert=True)
    await call.message.delete()