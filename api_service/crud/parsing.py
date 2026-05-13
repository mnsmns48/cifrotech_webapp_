from collections import OrderedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.price_sync.crud import load_origin_feature_map, load_unique_models_by_origins, \
    load_origins_attrs_map
from api_service.modulars.price_sync.func import filter_unique_origins_by_attrs
from api_service.schemas import ModelForApprove
from models import ParsingLine


async def render_models_structured_db(vsl_id: int, session: AsyncSession) -> list[ModelForApprove]:
    stmt = select(ParsingLine.origin).where(ParsingLine.vsl_id == vsl_id)
    rows = (await session.execute(stmt)).scalars().all()

    origin_feature_map = await load_origin_feature_map(parsing_origins=set(rows),
                                                       hubstock_origins=None,
                                                       session=session)

    models_list = await load_unique_models_by_origins(origin_feature_map, session)
    all_origin_ids = {o.origin for m in models_list for o in m.origins}
    attrs_map = await load_origins_attrs_map(all_origin_ids, session)
    filter_unique_origins_by_attrs(models_list, attrs_map)
    return models_list
