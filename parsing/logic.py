import asyncio
import importlib.util
from pathlib import Path

from aiohttp import ClientSession
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.api_req import get_one_by_dtube, get_items_by_brand
from api_service.crud import delete_harvest_strings_by_vsl_id, store_one_item
from api_service.schemas import ParsingRequest
from api_service.utils import normalize_origin
from config import BASE_DIR
from models import Vendor


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
        collected_data: dict = await pars_obj.process()
    finally:
        await pars_obj.browser.close()
        await pars_obj.playwright.stop()
    if len(collected_data['data']) > 0:
        await append_info(session=session, data=collected_data)
    return collected_data


async def append_info(session: AsyncSession, data: dict):
    lines: list[dict] = data["data"]
    origins: list[str] = [line["origin"] for line in lines]

    # cashed: dict[str, dict] = await get_info_by_detail_dependencies(session, origins)
    async def process_line(line: dict, aio: ClientSession):
        origin = normalize_origin(line.get("origin"))
        if not origin:
            return
        # cached = cashed.get(origin)
        # if cached:
        #     line["title"] = cached["title"]
        #     line["info"] = cached["info"]
        #     return

        result = await get_one_by_dtube(session=aio, title=line["title"])
        if result:
            await store_one_item(session=session, origin=origin, data=result)
            await session.commit()
            line["feature"] = {'result': result}
        else:
            brand_items = await get_items_by_brand(session=aio, title=line["title"])
            if not brand_items:
                return
            for item in brand_items:
                await store_one_item(session=session, origin=origin, data=item)
        await session.commit()
    async with ClientSession() as client_session:
        await asyncio.gather(*(process_line(line, client_session) for line in lines))
    return data
