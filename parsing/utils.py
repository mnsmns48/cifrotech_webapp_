import asyncio
import math
from typing import Any

import aiofiles
from aiohttp import ClientSession
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.api_req import get_one_by_dtube, get_items_by_brand
from api_service.crud import get_info_by_detail_dependencies, store_detail_dependencies


def cost_process(n, reward_ranges):
    for line_from, line_to, is_percent, extra in reward_ranges:
        if line_from <= n < line_to:
            if is_percent:
                addition = n * extra / 100
            else:
                addition = extra
            result = n + addition
            return math.ceil(result / 100) * 100
    return n


def cost_value_update(items: list[dict], ranges: list) -> list:
    for item in items:
        if item['origin'] and item['input_price']:
            item['output_price'] = cost_process(item['input_price'], ranges)
    return items


async def append_info(session: AsyncSession, data: dict):
    lines: list[dict] = data["data"]
    origins: list[str] = [line["origin"] for line in lines]
    cashed: dict[str, dict] = await get_info_by_detail_dependencies(session, origins)

    async def process_line(line: dict, aio: ClientSession):
        origin = line.get("origin")
        if not origin:
            return
        cached = cashed.get(origin)
        if cached:
            line["info"] = cached["info"]
            line["title"] = cached["title"]
            return
        result = await get_one_by_dtube(session=aio, title=line["title"])
        if not result:
            brand_resp = await get_items_by_brand(session=aio, title=line["title"])
            result = brand_resp.get("result") if brand_resp else {}
        if 'result' in result.keys():
            line["info"] = result
        else:
            line["info"] = {'result': result}
        to_store = {
            "origin": origin,
            "title": line["title"],
            "info": line["info"],
        }
        await store_detail_dependencies(session=session, data=to_store)

    async with ClientSession() as client_session:
        await asyncio.gather(*(process_line(line, client_session) for line in lines))
    return data
