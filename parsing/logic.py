import asyncio
import importlib.util
from functools import partial
from pathlib import Path

from aiohttp import ClientSession
from pyexpat import features
from redis.asyncio import Redis
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.api_req import get_one_by_dtube, get_items_by_brand
from api_service.crud import delete_harvest_strings_by_vsl_id, store_one_item, get_info_by_caching, \
    add_dependencies_link
from api_service.schemas import ParsingRequest
from api_service.utils import normalize_origin
from config import BASE_DIR
from models import Vendor, ProductFeaturesLink


async def parsing_core(redis: Redis,
                       data: ParsingRequest,
                       vendor: Vendor,
                       session: AsyncSession,
                       function_name: str) -> dict:
    module_path = Path(f"{BASE_DIR}/parsing/sources/{function_name}.py")
    if not module_path.exists():
        raise FileNotFoundError(f"Функция {module_path} не найдена")
    module_name = f"parsing.sources.{function_name}"
    module = importlib.import_module(module_name)
    parser_class = getattr(module, "BaseParser")
    pars_obj = parser_class(redis, data, vendor, session)
    await pars_obj.run()
    try:
        await delete_harvest_strings_by_vsl_id(session=session, vsl_id=data.vsl_id)
        result: dict = await pars_obj.process()
    finally:
        await pars_obj.browser.close()
        await pars_obj.playwright.stop()
    result['data'] = await append_info(session=session, data_lines=result['data'])
    return result


# async def fetch_and_store_items(session: AsyncSession,
#                                 origin: int, title: str, client_session: ClientSession,
#                                 cache: dict[int, list[str]]) -> list[str]:
#     brand_items = await get_items_by_brand(session=client_session, title=title)
#     if not brand_items:
#         return []
#     for item in brand_items:
#         await store_one_item(session=session, origin=origin, data=item)
#     await session.commit()
#     titles = [item["title"] for item in brand_items]
#     cache[origin] = titles
#     return titles


async def append_info(session: AsyncSession, data_lines: list, is_again: bool = False):
    async with ClientSession() as client_session:
        origins = [normalize_origin(item.get("origin")) for item in data_lines]
        cached: dict[int, list[str]] = await get_info_by_caching(session, origins)
        if is_again:
            origins_to_delete = list()
            for origin, lst in cached.items():
                if len(lst) > 1:
                    origins_to_delete.append(origin)
            for origin in origins_to_delete:
                cached.pop(origin, None)
            if origins_to_delete:
                stmt = delete(ProductFeaturesLink).where(ProductFeaturesLink.origin.in_(origins_to_delete))
                await session.execute(stmt)
                await session.commit()
        missing_elements = set(origins) - set(cached.keys())
        if missing_elements:
            for line in data_lines:
                if 'origin' not in line:
                    continue
                origin = normalize_origin(line.get("origin"))
                if origin in missing_elements:
                    one_item = await get_one_by_dtube(session=client_session, title=line['title'])
                    if one_item:
                        feature_id = await store_one_item(session=session, data=one_item)
                        await add_dependencies_link(session=session, origin=origin, feature_id=feature_id)
                        cached[origin] = [one_item['title']]
                    else:
                        all_brand_items = await get_items_by_brand(session=client_session, title=line['title'])
                        if all_brand_items:
                            feature_ids = list()
                            for line_item in all_brand_items:
                                feature_id = await store_one_item(session=session, data=line_item)
                                await add_dependencies_link(session=session, origin=origin, feature_id=feature_id)
                                feature_ids.append(line_item['title'])
                            cached[origin] = feature_ids
                        else:
                            cached[origin] = []
        if len(cached.keys()) == len(origins):
            for line in data_lines:
                origin = normalize_origin(line.get("origin"))
                line["features_title"] = cached.get(origin)
    return data_lines
