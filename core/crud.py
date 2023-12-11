from functools import wraps
from typing import Dict, Sequence
from sqlalchemy import select, Result
from sqlalchemy.ext.asyncio import AsyncSession
from core.description.description_models import s_main, display, energy, camera, performance
from core.models import StockTable
from support_func import month_convert, resolution_convert, name_cut
from cfg import disabled_buttons, dir_with_desc


async def get_directory(session_pg: AsyncSession,
                        parent: int) -> Dict[str, list]:
    destination_folder = bool()
    stmt = (
        select(StockTable)
        .where(StockTable.parent == parent)
        .filter(StockTable.name.not_in(disabled_buttons))
        .order_by(StockTable.price)
    )
    result: Result = await session_pg.execute(stmt)
    product = list(result.scalars().all())
    for line in product:
        destination_folder = False if line.code < 1000 else True
    output = {'product_list': product, 'destination_folder': destination_folder}
    return output


async def get_product(session: AsyncSession, code: int) -> StockTable | None:
    return await session.get(StockTable, code)


async def get_description(session_desc: AsyncSession, models: list):
    stmt = select(
        s_main.c.title,
        s_main.c.category,
        s_main.c.release_date,
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
        performance.c.lithography_process,
        performance.c.total_score,
        s_main.c.advantage,
        s_main.c.disadvantage) \
        .where(
        (s_main.c.title.in_(models)) &
        (s_main.c.title == display.c.title) &
        (s_main.c.title == energy.c.title) &
        (s_main.c.title == camera.c.title) &
        (s_main.c.title == performance.c.title)
    )
    result: Result = await session_desc.execute(stmt)
    response_list = result.fetchall()
    description_list = dict()
    for model in response_list:
        description_list.update(
            {model[0]:
                 [f"Класс <b>{str(model[1])}</b><br>"
                  f"Дата выхода <b>{month_convert(model[2])}</b><br>"
                  f"Дисплей <b>{model[3]}' {model[4]} {resolution_convert(model[6])} {model[5]} Hz</b><br>"
                  f"АКБ <b>{model[7]} mAh, мощность заряда {int(model[8])} W</b><br>"
                  f"Быстрая зарядка <b>{model[9]}</b><br>"
                  f"Основные камеры <b>{model[10]}</b><br>"
                  f"Фронтальная камера <b>{int(model[11])} Мп</b><br>"
                  f"Процессор <b>{model[12]} {model[13]}нм</b><br>"
                  f"Оценка производительности Antutu <b>{model[14]}</b><br>",
                  f"{' '.join(model[15])}<br>",
                  f"{' '.join(model[16])}<br>"
                  ]
             }
        )
    return description_list


def description(coroutine):
    @wraps(coroutine)
    async def wrapper(*args, **kwargs):
        response = await coroutine(*args, **kwargs)
        if kwargs.get('parent') in dir_with_desc:
            names = list()
            for line in response:
                name = name_cut(line.name)
                names.append(name)
            response_description = await get_description(session_desc=kwargs.get('session_desc'), models=names)
            for line in response:
                line.desc = response_description.get(name_cut(line.name))
        return response

    return wrapper


async def get_parent_path(session_pg: AsyncSession, code: int):
    sub = select(StockTable.parent).where(StockTable.code == code).scalar_subquery()
    query = select(StockTable).where(StockTable.parent == sub).filter(StockTable.name.not_in(disabled_buttons))
    result: Result = await session_pg.execute(query)
    parents = result.scalars().all()
    return parents


@description
async def get_product_list(session_pg: AsyncSession, session_desc: AsyncSession, parent: int) -> Sequence:
    subquery = select(StockTable.code).where(StockTable.parent == parent).scalar_subquery()
    stmt = select(StockTable).where(StockTable.code.in_(subquery)).order_by(StockTable.price)
    result: Result = await session_pg.execute(stmt)
    products = result.scalars().all()
    return products


@description
async def get_product_list_in_parent(session_pg: AsyncSession, session_desc: AsyncSession, parent: int) -> Sequence:
    subquery = select(StockTable.code).where(StockTable.parent == parent).scalar_subquery()
    stmt = select(StockTable) \
        .where(StockTable.parent.in_(subquery)) \
        .order_by(StockTable.price) \
        .limit(50)
    result: Result = await session_pg.execute(stmt)
    products = result.scalars().all()
    return products


