from datetime import datetime, UTC, timedelta
from typing import Optional, List, Dict

from loguru import logger
from sqlalchemy import select, func, case
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.dao.base import BaseDAO
from bot.dao.models import User, Purchase, Category, Product


class CategoryDao(BaseDAO[Category]):
    model = Category


class ProductDao(BaseDAO[Product]):
    model = Product


class PurchaseDao(BaseDAO[Purchase]):
    model = Purchase

    @classmethod
    async def get_full_sum(cls, session: AsyncSession) -> int:
        """Получить общую сумму покупок."""
        query = select(func.sum(cls.model.price).label('total_price'))
        result = await session.execute(query)
        total_price = result.scalars().one_or_none()
        return total_price if total_price is not None else 0


class UserDAO(BaseDAO[User]):
    model = User

    @classmethod
    async def get_purchase_statistics(
        cls, session: AsyncSession, telegram_id: int) -> Optional[Dict[str, int]]:
        """
        Метод возвращает общее количество покупок и их сумму для
        конкретного пользователя по его Telegram ID.
        """
        try:
            # Запрос для получения общего числа покупок и общей суммы
            result = await session.execute(
                select(func.count(Purchase.id).label('total_purchases'), func.sum(Purchase.price).label('total_amount'))
                .join(User)
                .filter(User.telegram_id == telegram_id)
            )
            stats = result.one_or_none()
            if stats is None:
                return None
            total_purchases, total_amount = stats
            return {
                'total_purchases': total_purchases,
                'total_amount': total_amount or 0,  # Обработка случая, когда сумма может быть None
            }
        except SQLAlchemyError as e:
            # Обработка ошибок при работе с базой данных
            print(f'Ошибка при получении статистики покупок пользователя: {e}')
            return None

    @classmethod
    async def get_purchased_products(
        cls, session: AsyncSession, telegram_id: int) -> Optional[List[Purchase]]:
        """
        Метод возвращает список всех покупок пользователя с детализацией по продуктам.
        """
        try:
            # Запрос для получения пользователя с его покупками и связанными продуктами
            result = await session.execute(
                select(User)
                .options(selectinload(User.purchases).selectinload(Purchase.product))
                .filter(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                return None
            return user.purchases
        except SQLAlchemyError as e:
            # Обработка ошибок при работе с базой данных
            print(f'Ошибка при получении информации о покупках пользователя: {e}')
            return None

    @classmethod
    async def get_statistics(cls, session: AsyncSession):
        """
        Метод собирает данные о количестве пользователей,
        зарегистрированных за различные временные периоды.
        """
        try:
            now = datetime.now(UTC)

            query = select(
                func.count().label('total_users'),
                func.sum(case((cls.model.created_at >= now - timedelta(days=1), 1), else_=0)).label('new_today'),
                func.sum(case((cls.model.created_at >= now - timedelta(days=7), 1), else_=0)).label('new_week'),
                func.sum(case((cls.model.created_at >= now - timedelta(days=30), 1), else_=0)).label('new_month')
            )

            result = await session.execute(query)
            stats = result.fetchone()

            statistics = {
                'total_users': stats.total_users,
                'new_today': stats.new_today,
                'new_week': stats.new_week,
                'new_month': stats.new_month
            }

            logger.info(f'Статистика успешно получена: {statistics}')
            return statistics
        except SQLAlchemyError as e:
            logger.error(f'Ошибка при получении статистики: {e}')
            raise