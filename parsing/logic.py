import importlib.util
from pathlib import Path
from typing import Any

from aiobotocore.client import AioBaseClient
from aiohttp import ClientSession
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.annotation import Annotated

from api_service.api_req import get_one_by_dtube
from api_service.crud import delete_harvest_strings_by_vsl_id, store_one_item, get_info_by_caching, \
    add_dependencies_link
from api_service.routers.s3_helper import build_with_preview

from api_service.schemas import ParsingRequest
from api_service.utils import normalize_origin
from config import BASE_DIR
from models import Vendor


async def parsing_core(redis: Redis,
                       data: ParsingRequest,
                       vendor: Vendor,
                       session: AsyncSession,
                       function_name: str,
                       s3_client: AioBaseClient) -> dict:
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
    result['data'] = await append_info(session=session, data_lines=result['data'], redis=redis, channel=data.progress,
                                       sync_features=data.sync_features)
    result['data'] = await build_with_preview(session=session, data_lines=result['data'], s3_client=s3_client)
    return result


async def append_info(session: AsyncSession,
                      data_lines: list,
                      sync_features: bool,
                      redis: Redis = None,
                      channel: str = None):
    async with ClientSession() as client_session:
        origins = [normalize_origin(item.get("origin")) for item in data_lines]
        cached: dict[int, list[str]] = await get_info_by_caching(session, origins)
        missing = set(origins) - set(cached.keys())
        if sync_features and missing:
            if redis and channel:
                await redis.publish(channel, f"data: COUNT={len(missing)}")
            for line in data_lines:
                origin = normalize_origin(line.get("origin"))
                if origin not in missing:
                    continue
                one_item = await get_one_by_dtube(session=client_session, title=line["title"])
                if one_item:
                    feature_id = await store_one_item(session=session, data=one_item)
                    await add_dependencies_link(session=session, origin=origin, feature_id=feature_id)
                    cached[origin] = [one_item["title"]]
                    if redis and channel:
                        await redis.publish(channel, f"Добавление {one_item['title']}")
                else:
                    cached[origin] = []
        if not sync_features:
            for origin in missing:
                cached[origin] = []
        for line in data_lines:
            origin = normalize_origin(line.get("origin"))
            line["features_title"] = cached.get(origin, [])
    return data_lines
