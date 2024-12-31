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


