from typing import Any

from sqlalchemy import func, select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from models import Products

bind_words = [
    'plus',
    'pro',
    'max',
    'ultra',
    'neo',
    'lite',
    'ne'
]



async def no_digits(text_str: str) -> bool:
    for char in text_str:
        if char.isdigit():
            return False
    return True


async def check_tsv(words: list, tsv: str) -> bool:
    for word in words:
        if word == tsv:
            return True
        if await no_digits(text_str=word):
            if word[:-1] == tsv:
                return True
    return False


async def check_binding_words(search_words: list, tsv_list: list) -> bool:
    for word in search_words:
        if word in bind_words:
            if word in tsv_list:
                return True
            else:
                return False
    return True


async def query_string_formating(text_string: str) -> list:
    input_string = text_string.replace('+', ' plus')
    working_string = input_string.lower()
    result = []
    i = 0
    while i < len(working_string):
        matched = False
        for word in bind_words:
            if working_string[i:i + len(word)] == word:
                result.append(input_string[i:i + len(word)].lower())
                i += len(word)
                matched = True
                break
        if not matched:
            result.append(input_string[i].lower())
            i += 1
    return ''.join(result).split()


async def search_devices(session: AsyncSession,
                         query_string: str,
                         conditions: dict[str, Any] = None) -> Products | None:
    query_words = await query_string_formating(text_string=query_string)
    tsquery_string = " | ".join(query_words)
    ts_query = func.to_tsquery('simple', tsquery_string)
    query = select(Products,
                   func.ts_rank(Products.title_tsv, ts_query).label('rank'),
                   func.length(Products.title_tsv).label('length'))
    where_conditions = list()
    if conditions:
        for column, value in conditions.items():
            column = getattr(Products, column)
            where_conditions.append(column == value)
    query = query.filter(and_(
        func.length(Products.title_tsv) >= 1),
        Products.title_tsv.op('@@')(ts_query), *where_conditions)
    query = query.order_by(text('rank DESC')).limit(5)
    execute_obj = await session.execute(query)
    for line in execute_obj.all():
        result = line[0]
        device_obj = dict()
        tsv_list = [tsj_obj.split(':')[0].strip("'") for tsj_obj in result.title_tsv.split()]
        fail_tsv_attributes = tsv_list.copy()
        for tsv in tsv_list:
            tsv_value = await check_tsv(words=query_words, tsv=tsv)
            if tsv_value:
                device_obj.setdefault(result.title, []).append(True)
                fail_tsv_attributes.remove(tsv)
            else:
                device_obj.setdefault(result.title, []).append(False)
        tsv_check = await check_binding_words(search_words=query_words, tsv_list=tsv_list)
        if all(device_obj[result.title]) and (not fail_tsv_attributes) and tsv_check:
            return result
