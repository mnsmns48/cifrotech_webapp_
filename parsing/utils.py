import math

from aiohttp import ClientSession
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.api_req import get_one_by_dtube, get_items_by_brand
from api_service.crud import get_info_by_origins, store_detail_dependencies


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


async def append_info(session: AsyncSession, data: dict) -> dict:
    origins = [item['origin'] for item in data['data']]
    cashed: dict = await get_info_by_origins(session, origins)
    async with ClientSession() as aio_session:
        for line in data['data']:
            if line['origin'] in cashed.keys():
                line['info'] = cashed.get(line['origin']).get('info')
                line['title'] = cashed.get(line['origin']).get('title')
            else:
                result = await get_one_by_dtube(session=aio_session, title=line['title'])
                if result:
                    data_to_store = {
                        'origin': line['origin'],
                        'title': line['title']
                    }
                    if 'result' in result.keys():
                        line['info'] = result['result']
                    else:
                        line['info'] = result
                        data_to_store['info'] = result
                    await store_detail_dependencies(session=session, data=data_to_store)
                else:
                    by_brand_list = await get_items_by_brand(session=aio_session, title=line['title'])
                    line['info'] = by_brand_list['result']
    return data
