import json
import re
import time
from sqlalchemy import select, Result, func, literal
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from api_v2.schemas import Menu
from cfg import disabled_buttons, core_config, settings
from models import StockTable


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


async def get_page_items(items_key, session_pg: AsyncSession):
    stmt = (
        select(StockTable)
        .where(StockTable.parent == items_key)
        .filter(StockTable.name.not_in(disabled_buttons))
        .order_by(StockTable.price)
    )
    fetch: Result = await session_pg.execute(stmt)
    data = fetch.scalars().all()
    result = list()
    for row in data:
        result.append({'code': row.code,
                       'name': row.name,
                       'qty': row.quantity,
                       'price': row.price})
    json_result = json.dumps(result, ensure_ascii=False, indent=2)
    return json_result
