from botocore.exceptions import BotoCoreError, ClientError
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.routers.s3_helper import build_with_preview
from config import settings
from models import HarvestLine, ProductOrigin
from parsing.logic import append_info


async def _fetch_and_build_harvest_lines(session: AsyncSession, harvest_id: int, s3_client) -> list[dict]:
    stmt = (
        select(HarvestLine, ProductOrigin)
        .join(ProductOrigin, HarvestLine.origin == ProductOrigin.origin)
        .where(
            and_(HarvestLine.harvest_id == harvest_id, ProductOrigin.is_deleted.is_(False))
        ).order_by(HarvestLine.input_price)
    )
    result = await session.execute(stmt)
    rows = result.all()
    encoded = list()
    for hl, origin in rows:
        hl_dict = jsonable_encoder(hl)
        origin_dict = jsonable_encoder(origin)
        combined = hl_dict.copy()
        combined.update(origin_dict)
        encoded.append(combined)
    result = await build_with_preview(session, encoded, s3_client)
    return result


async def _prepare_harvest_response(
        session: AsyncSession, redis, harvest_id: int, s3_client, channel: str | None = None,
        sync_features: bool = True) -> list:
    data_lines = await _fetch_and_build_harvest_lines(session, harvest_id, s3_client)
    processed = await append_info(session=session, data_lines=data_lines, redis=redis, channel=channel,
                                  sync_features=sync_features)
    if channel:
        await redis.publish(channel, "END")
    return processed