from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import HarvestLine, ProductOrigin
from parsing.logic import append_info


async def _fetch_and_build_harvest_lines(session: AsyncSession, harvest_id: int) -> list[dict]:
    stmt = (select(HarvestLine, ProductOrigin)
            .join(ProductOrigin, HarvestLine.origin == ProductOrigin.origin)
            .where(
        and_(
            HarvestLine.harvest_id == harvest_id,
            ProductOrigin.is_deleted.is_(False)
        )
    ).order_by(HarvestLine.input_price))
    result = await session.execute(stmt)
    rows = result.all()
    joined_encoded_data = list()
    for hl, origin in rows:
        d = jsonable_encoder(hl)
        d.update(jsonable_encoder(origin))
        joined_encoded_data.append(d)
    return joined_encoded_data


async def _prepare_harvest_response(
        session: AsyncSession, redis, harvest_id: int, channel: str | None = None,
        sync_features: bool = True) -> list:
    data_lines = await _fetch_and_build_harvest_lines(session, harvest_id)
    processed = await append_info(session=session, data_lines=data_lines, redis=redis, channel=channel,
                                  sync_features=sync_features)
    if channel:
        await redis.publish(channel, "END")
    return processed
