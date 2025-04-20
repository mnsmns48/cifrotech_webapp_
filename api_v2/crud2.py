import json
import re

from sqlalchemy import select, Result, func, literal, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api_v1.old_config import disabled_buttons
from models import StockTable


async def get_random12(session_pg: AsyncSession):
    query = (select(StockTable.code, StockTable.name, StockTable.quantity, StockTable.price)
             .where(StockTable.ispath == False).order_by(func.random()).limit(12))
    result = await session_pg.execute(query)
    random_products = result.fetchall()
    products = list()
    for product in random_products:
        products.append({"code": product.code,
                         "name": product.name,
                         "qty": product.quantity,
                         "price": product.price})
    json_result = json.dumps(products, ensure_ascii=False, indent=2)
    return json_result


async def get_root_menu(session_pg: AsyncSession):
    base = select(
        StockTable.code,
        StockTable.parent,
        StockTable.name,
        StockTable.ispath,
        func.concat(literal('{'), StockTable.code, literal(': '), StockTable.name, literal('}')).label("path")
    ).where(StockTable.parent == 0)
    cte = base.cte(name="cte", recursive=True)
    recursive_term = select(
        StockTable.code,
        StockTable.parent,
        StockTable.name,
        StockTable.ispath,
        func.concat(cte.c.path, literal(', '), literal('{'), StockTable.code, literal(': '), StockTable.name,
                    literal('}')).label("path")).select_from(
        StockTable.__table__.join(cte, StockTable.parent == cte.c.code)).where(StockTable.ispath == True)
    cte = cte.union_all(recursive_term)
    query = select(cte.c.path)
    fetch = await session_pg.execute(query)
    data = fetch.fetchall()

    def parse_row(line: str) -> list:
        row_list = list()
        parts = re.findall(r'\{([^}]+)\}', line.strip("'()"))
        for kv in parts:
            key, label = kv.split(": ")
            row_list.append((int(key), label))
        return row_list

    def add_to_tree(tokens: list[tuple], tree_dict: dict) -> None:
        current_level = tree_dict
        for key, label in tokens:
            if key not in current_level:
                current_level[key] = {"key": key, "label": label, "children": {}}
            current_level = current_level[key]["children"]

    def convert_tree(tree_dict: dict) -> list:
        result_list = list()
        for key, node in tree_dict.items():
            item = {"key": node["key"],
                    "label": node["label"]}
            children_list = convert_tree(node["children"])
            if children_list:
                item["children"] = children_list
            result_list.append(item)
        return result_list

    tree = dict()
    for row in data:
        tokens = parse_row(row[0])
        add_to_tree(tokens=tokens, tree_dict=tree)
    tree_list = convert_tree(tree)
    json_result = json.dumps(tree_list, ensure_ascii=False, indent=2)
    return json_result


async def get_page_items(items_key: int, session_pg: AsyncSession) -> str:
    result = list()

    async def fetch_items_recursive(key: int):
        stmt = (
            select(StockTable).filter(
                and_(StockTable.name.not_in(disabled_buttons),
                     StockTable.parent == key)).order_by(StockTable.price)
        )
        fetch: Result = await session_pg.execute(stmt)
        data = fetch.scalars().all()
        for row in data:
            if not row.ispath:
                item = {
                    'code': row.code,
                    'name': row.name,
                    'qty': row.quantity,
                    'price': row.price
                }
                if row.info:
                    item.update({'info': row.info})
                result.append(item)
            else:
                await fetch_items_recursive(row.code)

    await fetch_items_recursive(items_key)
    json_result = json.dumps(result, ensure_ascii=False, indent=2)
    return json_result
