from datetime import date, datetime, timedelta
from typing import List, Optional
from sqlalchemy import select, Result, update, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.schemas.api_v1_schemas import SaleItemScheme
from app_utils import format_datetime_ru
from bot.user.schemas import HubMenuLevel, HubStockResponse, HubStockItem
from models import Guests, TgBotOptions, HUbMenuLevel, HUbStock, ProductOrigin, ProductFeaturesLink


async def user_spotted(session: AsyncSession, data: dict) -> None:
    await session.execute(insert(Guests), data)
    await session.commit()


async def get_option_value(session: AsyncSession, username, field):
    stmt = select(TgBotOptions).filter(TgBotOptions.username == username)
    result: Result = await session.execute(stmt)
    option_obj = result.scalars().first()
    return getattr(option_obj, field) if option_obj else None


async def add_bot_options(session: AsyncSession, **kwargs):
    if kwargs:
        await session.execute(insert(TgBotOptions).values(kwargs))
        await session.commit()


async def update_bot(session: AsyncSession, **kwargs):
    if kwargs:
        await session.execute(update(TgBotOptions).filter(TgBotOptions.username == kwargs.get('username'))
                              .values(main_pic=kwargs.get('main_pic')))
        await session.commit()


async def show_day_sales(session: AsyncSession, current_date: date) -> List[SaleItemScheme]:
    stmt = text(
        f"""
        SELECT activity.operation_code,
               activity.time_,
               activity.product_code,
               activity.product,
               activity.quantity,
               activity.sum_,
               activity.noncash,
               activity.return_,
               stocktable.quantity AS remain
        FROM activity
        LEFT OUTER JOIN stocktable ON stocktable.code = activity.product_code
        WHERE CAST(activity.time_ AS DATE) = '{current_date}'
        ORDER BY activity.time_
        """
    )

    result: Result = await session.execute(stmt)
    rows = result.all()

    sales: List[SaleItemScheme] = []
    for row in rows:
        data = row._mapping
        sales.append(SaleItemScheme(time_=data["time_"],
                                    product=data["product"],
                                    quantity=data["quantity"],
                                    sum_=data["sum_"],
                                    noncash=data["noncash"],
                                    return_=data["return_"],
                                    remain=data["remain"])
                     )

    return sales


async def get_menu_levels(session: AsyncSession, parent_id: int = 1) -> List[HubMenuLevel]:
    query = select(HUbMenuLevel).where(HUbMenuLevel.parent_id == parent_id).order_by(HUbMenuLevel.sort_order)
    execute = await session.execute(query)
    levels = execute.scalars().all()
    result: List[HubMenuLevel] = list()
    for level in levels:
        result.append(HubMenuLevel.model_validate(level))
    return result


async def get_labels_by_ids(session: AsyncSession, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    query = select(HUbMenuLevel).where(HUbMenuLevel.id.in_(ids))
    execute = await session.execute(query)
    levels = execute.scalars().all()
    return {level.id: level.label for level in levels}


async def get_hubstock_items(session: AsyncSession, path_id: int) -> Optional[HubStockResponse]:
    stmt = (
        select(
            HUbStock.output_price,
            HUbStock.updated_at,
            HUbStock.origin,
            ProductOrigin.title,
            ProductFeaturesLink.feature_id
        )
        .join(ProductOrigin, ProductOrigin.origin == HUbStock.origin)
        .join(ProductFeaturesLink, ProductFeaturesLink.origin == ProductOrigin.origin)
        .where(HUbStock.path_id == path_id)
        .order_by(ProductFeaturesLink.feature_id, HUbStock.output_price)
    )

    result = await session.execute(stmt)
    rows = result.all()

    items = [
        HubStockItem(title=row.title, price=row.output_price, origin=row.origin)
        for row in rows if row.output_price is not None
    ]

    updated_dates: List[datetime] = [row.updated_at for row in rows]
    latest_updated_at = max(updated_dates) if updated_dates else None
    if latest_updated_at:
        latest_updated_at = latest_updated_at + timedelta(hours=3)
        formatted_date = format_datetime_ru(latest_updated_at) if latest_updated_at else None

        return HubStockResponse(items=items, most_common_updated_at=formatted_date)
