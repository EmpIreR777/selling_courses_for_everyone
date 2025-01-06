from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from bot.config import bot, settings
from bot.dao.dao import UserDAO, CategoryDao, ProductDao, PurchaseDao
from bot.user.kbs import main_user_kb, catalog_kb, product_kb, get_product_buy_kb
from bot.user.schemas import TelegramIDModel, ProductCategoryIDModel, PaymentData


catalog_router = Router()


@catalog_router.callback_query(F.data == 'catalog')
async def page_catalog(call: CallbackQuery, session_without_commit: AsyncSession):
    await call.answer('Загрузка каталога...')
    catalog_data = await CategoryDao.find_all(session=session_without_commit)
    await call.message.edit_text(
        text='Выберите категорию товаров:',
        reply_markup=catalog_kb(catalog_data)
    )


@catalog_router.callback_query(F.data.startswith('category_'))
async def page_catalog_products(call: CallbackQuery, session_without_commit: AsyncSession):
    category_id = int(call.data.split('_')[-1])
    products_category = await ProductDao.find_all(
        session=session_without_commit, 
        filters=ProductCategoryIDModel(category_id=category_id))
    count_products = len(products_category)
    if count_products:
        await call.answer(f'В данной категории {count_products} товаров.')
        for product in products_category:
            product_text = (
                f'📦 <b>Название товара:</b> {product.name}\n\n'
                f'💰 <b>Цена:</b> {product.price} руб.\n\n'
                f'📝 <b>Описание:</b>\n<i>{product.description}</i>\n\n'
                f'━━━━━━━━━━━━━━━━━━'
            )
            await call.message.answer(
                product_text,
                reply_markup=product_kb(product.id, product.price)
            )
    else:
        await call.answer('В данной категории нет товаров.')


@catalog_router.callback_query(F.data.startswith('buy_'))
async def process_about(call: CallbackQuery, session_without_commit: AsyncSession):
    user_info = await UserDAO.find_one_or_none(
        session=session_without_commit,
        filters=TelegramIDModel(telegram_id=call.from_user.id)
    )
    _, product_id, price = call.data.split('_')
    await bot.send_invoice(
        chat_id=call.from_user.id,
        title=f'Оплата 👉 {price}₽',
        description=f'Пожалуйста, завершите оплату в размере {price}₽, чтобы открыть доступ к выбранному товару.',
        payload=f'{user_info.id}_{product_id}',
        provider_token=settings.PROVIDER_TOKEN,
        currency='rub',
        prices=[LabeledPrice(
            label=f'Оплата {price}',
            amount=int(price) * 100
        )],
        reply_markup=get_product_buy_kb(price)
    )
    await call.message.delete()


@catalog_router.pre_checkout_query(lambda query: True)
async def pre_checkout_query(pre_checkout_q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


@catalog_router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: Message, session_with_commit: AsyncSession):
    payment_info = message.successful_payment
    user_id, product_id = payment_info.invoice_payload.split('_')
    payment_data = {
        'user_id': int(user_id),
        'payment_id': payment_info.telegram_payment_charge_id,
        'price': payment_info.total_amount / 100,
        'product_id': int(product_id)
    }
    # Добавляем информацию о покупке в базу данных
    await PurchaseDao.add(session=session_with_commit, values=PaymentData(**payment_data))
    product_data = await ProductDao.find_one_or_none_by_id(session=session_with_commit, data_id=int(product_id))

    # Формируем уведомление администраторам
    for admin_id in settings.ADMIN_IDS:
        try:
            username = message.from_user.username
            user_info = f'@{username} ({message.from_user.id})' if username else f'c ID {message.from_user.id}'

            await bot.send_message(
                chat_id=admin_id,
                text=(
                    f'💲 Пользователь {user_info} купил товар <b>{product_data.name}</b> (ID: {product_id}) '
                    f'за <b>{product_data.price} ₽</b>.'
                )
            )
        except Exception as e:
            logger.error(f'Ошибка при отправке уведомления администраторам: {e}')

    # Подготавливаем текст для пользователя
    file_text = '📦 <b>Товар включает файл:</b>' if product_data.file_id else '📄 <b>Товар не включает файлы:</b>'
    product_text = (
        f'🎉 <b>Спасибо за покупку!</b>\n\n'
        f'🛒 <b>Информация о вашем товаре:</b>\n'
        f'━━━━━━━━━━━━━━━━━━\n'
        f'🔹 <b>Название:</b> <b>{product_data.name}</b>\n'
        f'🔹 <b>Описание:</b>\n<i>{product_data.description}</i>\n'
        f'🔹 <b>Цена:</b> <b>{product_data.price} ₽</b>\n'
        f'🔹 <b>Закрытое описание:</b>\n<i>{product_data.hidden_content}</i>\n'
        f'━━━━━━━━━━━━━━━━━━\n'
        f'{file_text}\n\n'
        f'ℹ️ <b>Информацию о всех ваших покупках вы можете найти в личном профиле.</b>'
    )

    # Отправляем информацию о товаре пользователю
    if product_data.file_id:
        await message.answer_document(
            document=product_data.file_id,
            caption=product_text,
            reply_markup=main_user_kb(message.from_user.id)
        )
    else:
        await message.answer(
            text=product_text,
            reply_markup=main_user_kb(message.from_user.id)
        )