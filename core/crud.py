from typing import Dict, Sequence
from sqlalchemy import select, Result
from sqlalchemy.ext.asyncio import AsyncSession

from core.description.description_models import s_main, display, energy, camera, performance
from core.models import StockTable
from support_func import month_convert, resolution_convert, name_cut
from cfg import disabled_buttons


async def get_directory(session: AsyncSession, parent: int) -> Dict[str, list]:
    destination_folder = bool()
    stmt = (
        select(StockTable)
        .where(StockTable.parent == parent)
        .filter(StockTable.name.not_in(disabled_buttons))
        .order_by(StockTable.price)
    )
    result: Result = await session.execute(stmt)
    product = list(result.scalars().all())
    for line in product:
        destination_folder = False if line.code < 1000 else True
    output = {'product_list': product, 'destination_folder': destination_folder}
    return output


async def get_product(session: AsyncSession, code: int) -> StockTable | None:
    return await session.get(StockTable, code)


async def get_description(session: AsyncSession, models: list):
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
    result: Result = await session.execute(stmt)
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
                  f"Процессор <b>{model[12]}</b><br>"
                  f"Оценка производительности Antutu <b>{model[13]}</b><br>",
                  f"{' '.join(model[14])}<br>",
                  f"{' '.join(model[15])}<br>"
                  ]
             }
        )
    return description_list


async def get_products_in_parent(session_pg: AsyncSession,
                                 session_desc: AsyncSession,
                                 parent: int) -> Sequence:
    subquery = select(StockTable.code).where(StockTable.parent == parent)
    stmt = select(StockTable).where(StockTable.parent.in_(subquery)).order_by(StockTable.price)
    result: Result = await session_pg.execute(stmt)
    products = result.scalars().all()
    names = list()
    for line in products:
        name = name_cut(line.name)
        names.append(name)
    description = await get_description(session_desc, names)
    for line in products:
        line.desc = description.get(name_cut(line.name))
    return products
