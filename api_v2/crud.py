import json
import re

from sqlalchemy import select, Result, func, literal
from sqlalchemy.ext.asyncio import AsyncSession

from api_v2.schemas import Menu
from cfg import disabled_buttons
from models import StockTable


async def get_menu(session_pg: AsyncSession) -> list[Menu]:
    stmt = (
        select(StockTable)
        .where(StockTable.ispath == True)
        .filter(StockTable.name.not_in(disabled_buttons))
    )
    result: Result = await session_pg.execute(stmt)
    result_dto = [Menu.model_validate(row, from_attributes=True) for row in result.scalars().all()]
    return result_dto


async def get_recursive_menu(session_pg: AsyncSession):
    base = select(
        StockTable.code,
        StockTable.parent,
        StockTable.name,
        StockTable.ispath,
        func.concat(
            literal('{'),
            StockTable.code,
            literal(': '),
            StockTable.name,
            literal('}')
        ).label("path")
    ).where(StockTable.parent == 0)
    cte = base.cte(name="cte", recursive=True)
    recursive_term = select(
        StockTable.code,
        StockTable.parent,
        StockTable.name,
        StockTable.ispath,
        func.concat(
            cte.c.path,
            literal(', '),
            literal('{'),
            StockTable.code,
            literal(': '),
            StockTable.name,
            literal('}')
        ).label("path")
    ).select_from(
        StockTable.__table__.join(cte, StockTable.parent == cte.c.code)
    ).where(StockTable.ispath == True)
    cte = cte.union_all(recursive_term)
    query = select(cte.c.path)
    result = await session_pg.execute(query)
    data = result.fetchall()
    tree = dict()

    def parse_line(line):
        line = line.strip()
        if line.startswith("(") and line.endswith(")"):
            line = line[1:-1]
        line = line.strip("'")
        parts = re.findall(r'\{([^}]+)\}', line)
        tokens = list()
        for part in parts:
            key_str, label = part.split(": ", 1)
            tokens.append((int(key_str.strip()), label.strip()))
        return tokens

    def add_to_tree(tokens):
        current_level = tree
        for key, label in tokens:
            if key not in current_level:
                current_level[key] = {"key": key, "label": label, "children": {}}
            current_level = current_level[key]["children"]

    def convert_tree(tree_dict):
        result = list()
        for key in tree_dict.keys():
            node = tree_dict[key]
            item = {
                "key": node["key"],
                "label": node["label"]
            }
            children_list = convert_tree(node["children"])
            if children_list:
                item["children"] = children_list
            result.append(item)
        return result

    for tup in data:
        line = tup[0]
        tokens = parse_line(line)
        add_to_tree(tokens)

    tree_list = convert_tree(tree)
    json_result = json.dumps(tree_list, ensure_ascii=False, indent=2)
    return json_result
