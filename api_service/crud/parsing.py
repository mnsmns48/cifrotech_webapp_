from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.price_sync.crud import load_origin_feature_map, load_unique_models_by_origins
from api_service.schemas import ModelForApprove
from models import ParsingLine


async def render_models_structured_db(vsl_id: int, session: AsyncSession) -> list[ModelForApprove]:
    stmt = select(ParsingLine.origin).where(ParsingLine.vsl_id == vsl_id)
    rows = (await session.execute(stmt)).scalars().all()

    origin_feature_map: dict[int, dict[str, int | bool]] = await load_origin_feature_map(parsing_origins=set(rows),
                                                                                         hubstock_origins=None,
                                                                                         session=session)
    models_list: list[ModelForApprove] = await load_unique_models_by_origins(origin_feature_map, session)
    return models_list
