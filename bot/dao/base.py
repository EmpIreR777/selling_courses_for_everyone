from typing import List, Any, TypeVar, Generic
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy import func, update as sqlalchemy_update, delete as sqlalchemy_delete
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from bot.dao.database import Base

# Объявляем типовой параметр T с ограничением, что это наследник Base
T = TypeVar('T', bound=Base)


class BaseDAO(Generic[T]):
    model: type[T]

    @classmethod
    async def find_one_or_none_by_id(cls, data_id: int, session: AsyncSession):
        # Найти запись по ID
        logger.info(f'Поиск {cls.model.__name__} c ID: {data_id}')
        try:
            query = select(cls.model).filter_by(id=data_id)
            result = await session.execute(query)
            record = result.scalar_one_or_none()
            if record:
                logger.info(f'Запись с ID {data_id} найдена.')
            else:
                logger.info(f'Запись с ID {data_id} не найдена.')
            return record
        except SQLAlchemyError as e:
            logger.error(f'Ошибка при поиске записи с ID {data_id}: {e}')

    @classmethod
    async def find_one_or_none(cls, session: AsyncSession, filters: BaseModel):
        # Найти одну запись по фильтрам
        filter_dict = filters.model_dump(exclude_unset=True)
        logger.info(f'Поиск одной записи {cls.model.__name__} по фильтрам: {filter_dict}')
        try:
            query = select(cls.model).filter_by(**filter_dict)
            result = await session.execute(query)
            record = result.scalar_one_or_none()
            if record:
                logger.info(f"Запись найдена по фильтрам: {filter_dict}")
            else:
                logger.info(f"Запись не найдена по фильтрам: {filter_dict}")
            return record
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске записи по фильтрам {filter_dict}: {e}")
            raise

    @classmethod
    async def find_all(cls, session: AsyncSession, filters: BaseModel | None = None):
        # Найти все записи по фильтрам
        filter_dict = filters.model_dump(exclude_unset=True) if filters else {}
        try:
            query = select(cls.model).filter_by(**filter_dict)
            result = await session.execute(query)
            records = result.scalars().all()
            logger.info(f'Найдено {len(records)} записей.')
            return records
        except SQLAlchemyError as e:
            logger.error(f'Ошибка при поиске всех записей по фильтрам {filter_dict}')
            raise e

    @classmethod
    async def add(cls, session: AsyncSession, values: BaseModel):
        # Добавить одну запись
        values_dict = values.model_dump(exclude_unset=True)
        logger.info(f'Добавление записи {cls.model.__name__} с параметрами: {values_dict}')
        new_instance = cls.model(**values_dict)
        session.add(new_instance)
        try:
            await session.flush()
            logger.info(f'Запись {cls.model.__name__} успешно добавлена.')
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f'Ошибка при добавление записи: {e}')
            raise e
        return new_instance

    @classmethod
    async def delete(cls, session: AsyncSession, filters: BaseModel):
        # Удалить записи по фильтру
        filter_dict = filters.model_dump(exclude_unset=True)
        logger.info(f'Удаление записей {cls.model.__name__} по фильтру: {filter_dict}')
        if not filter_dict:
            logger.error('Нужен хотя бы один фильтр для удаления.')
            raise ValueError('Нужен хотя бы один фильтр для удаления.')
        query = sqlalchemy_delete(cls.model).filter_by(**filter_dict)
        try:
            result = await session.execute(query)
            await session.flush()
            logger.info(f'Удалено {result.rowcount} записей.')
            return result.rowcount
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f'Ошибка при удалении записей: {e}')
            raise e

    @classmethod
    async def count(cls, session: AsyncSession, filters: BaseModel | None = None):
        # Подсчитать количество записей
        filter_dict = filters.model_dump(exclude_unset=True) if filters else {}
        logger.info(f"Подсчет количества записей {cls.model.__name__} по фильтру: {filter_dict}")
        try:
            query = select(func.count(cls.model.id)).filter_by(**filter_dict)
            result = await session.execute(query)
            count = result.scalar()
            logger.info(f'Найдено {count} записей.')
            return count
        except SQLAlchemyError as e:
            logger.error(f'Ошибка при подсчете записей: {e}')
            raise e
