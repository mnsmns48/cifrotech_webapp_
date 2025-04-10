import asyncio
import re

from aiohttp import ClientSession
from sqlalchemy.ext.asyncio import AsyncSession

from bot.api_digitaltube import get_one_item


symbols_to_remove = ['-', '—']


def sanitize(text, symbols) -> str:
    remove_set = ''.join(map(re.escape, symbols))
    sanitized_text = re.sub(f"^[{remove_set}]+|[{remove_set}]+$", '', text)
    return sanitized_text


# def parse_product_message(text) -> list:
#     lines = text.splitlines()
#     products = list()
#     for line in lines:
#         line = line.strip()
#         if not line:
#             continue
#         match = re.search(r'(\d{4,6})\s*$', line)
#         if match:
#             price = int(match.group(1))
#             name = line[:match.start()].strip()
#             products.append({"title": sanitize(name, symbols_to_remove), "price": price})
#     return products
#
# async def working_under_product_list(pg_session: AsyncSession, cl_session: ClientSession, products: list[dict]):
#     for product_line in products:
#         product_obj = await search_devices(session=pg_session, query_string=product_line['title'].replace(')', ' ').replace('(', ' ').replace('!', ' '))
#         print('search_devices', product_obj)
#         if not product_obj:
#             product_obj = await get_one_item(session=cl_session, query_string=product_line['title'].replace(')', ' ').replace('(', ' ').replace('!', ' '))
#         print('get_one_item', product_obj)
#         await asyncio.sleep(0.1)