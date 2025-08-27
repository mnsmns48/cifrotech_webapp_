import importlib.util
from pathlib import Path
from typing import Any, List, Coroutine, Optional

from aiobotocore.client import AioBaseClient
from aiohttp import ClientSession
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.annotation import Annotated

from api_service.api_connect import get_one_by_dtube
from api_service.crud import store_one_item, get_info_by_caching, add_dependencies_link, get_rr_obj, \
    store_parsing_lines, append_info
from api_service.s3_helper import build_with_preview

from api_service.schemas import ParsingRequest, ParsingLinesIn
from api_service.schemas.parsing_schemas import SourceContext, ParsingResultOut
from api_service.utils import normalize_origin
from config import BASE_DIR

from parsing.utils import cost_value_update


async def parsing_core(redis: Redis, session: AsyncSession, s3_client: AioBaseClient,
                       progress: str, context: SourceContext, sync_features: bool) -> Optional[ParsingResultOut]:
    module_path = Path(f"{BASE_DIR}/parsing/sources/{context.vendor.function}.py")
    if not module_path.exists():
        raise FileNotFoundError(f"Функция {module_path} не найдена")
    module_name = f"parsing.sources.{context.vendor.function}"
    module = importlib.import_module(module_name)
    parser_class = getattr(module, "BaseParser")
    pars_obj = parser_class(redis, progress, context.vendor, context.vsl.url, session)
    await pars_obj.run()
    try:
        unclean_parsed_lines: List[ParsingLinesIn] = await pars_obj.get_parsed_lines()
        ranges = await get_rr_obj(session=session)
        with_added_cost = cost_value_update(items=unclean_parsed_lines, ranges=ranges.ranges)
        stored_items = await store_parsing_lines(
            session=session, items=with_added_cost, vsl_id=context.vsl.id, profit_range_id=ranges.id
        )
        if len(stored_items.parsing_result) > 0:
            await session.commit()
            stored_items.is_ok = True
    finally:
        await pars_obj.browser.close()
        await pars_obj.playwright.stop()
    await append_info(session=session,
                      data_lines=stored_items.parsing_result,
                      redis=redis,
                      channel=progress,
                      sync_features=sync_features
                      )
    await build_with_preview(session=session,
                             data_lines=stored_items.parsing_result,
                             s3_client=s3_client)
    return stored_items
