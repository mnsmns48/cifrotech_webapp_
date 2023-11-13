from typing import Dict, Any

from sqlalchemy import select, Result, Row, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from core.description.description_models import s_main, display, energy, camera, performance
from core.models import StockTable
from support_func import month_conv, resolution_conv


async def get_directory(session: AsyncSession, parent: int) -> Dict[str, list]:
    destination_folder = bool()
    stmt = (
        select(StockTable).where(StockTable.parent == parent).order_by(StockTable.price)
    )
    result: Result = await session.execute(stmt)
    product = tuple(result.scalars().all())
    for line in product:
        destination_folder = False if line.code < 1000 else True
    output = {'product_list': list(product), 'destination_folder': destination_folder}
    return output


async def get_product(session: AsyncSession, code: int) -> StockTable | None:
    return await session.get(StockTable, code)


async def get_products_in_parent(session: AsyncSession, parent: int) -> tuple[Row | RowMapping | Any, ...]:
    subquery = select(StockTable.code).where(StockTable.parent == parent)
    stmt = select(StockTable).where(StockTable.parent.in_(subquery)).order_by(StockTable.price)
    result: Result = await session.execute(stmt)
    product = tuple(result.scalars().all())
    return product


#
async def get_description(session: AsyncSession, model: list):
    stmt = select(
        s_main.c.release_date,
        s_main.c.category,
        display.c.d_size,
        display.c.display_type,
        display.c.refresh_rate,
        display.c.resolution,
        energy.c.capacity,
        energy.c.max_charge_power,
        energy.c.fast_charging,
        camera.c.lenses,
        camera.c.megapixels_front,
        performance.c.chipset,
        performance.c.total_score,
        s_main.c.advantage,
        s_main.c.disadvantage) \
        .where(
        (s_main.c.title.in_(model)) &
        (s_main.c.title == display.c.title) &
        (s_main.c.title == energy.c.title) &
        (s_main.c.title == camera.c.title) &
        (s_main.c.title == performance.c.title)
    )
    result: Result = await session.execute(stmt)
    response_list = result.fetchall()
    features = dict()
    description_list = list()
    for descript in response_list:
        features = dict()
        features.update(
            {
                'Класс': str(descript[0]),
                'Дата выхода': month_conv(descript[1]),
                'Дисплей': f"{descript[2]}' {descript[3]} {resolution_conv(descript[5])} {descript[4]} Hz",
                'АКБ': f"{descript[6]}, мощность заряда {int(descript[7])} W",
                'Быстрая зарядка': descript[8],
                'Основные камеры': descript[9],
                'Фронтальная камера': f"{int(descript[10])} Мп",
                'Процессор': descript[11],
                'Оценка производительности': descript[12],
                'Преимущества': descript[13],
                'Недостатки': descript[14]
            }
        )
        description_list.append(features)
    return description_list
