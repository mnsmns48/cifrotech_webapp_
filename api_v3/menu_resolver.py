import random
from typing import List, Dict, Set
from sqlalchemy import select, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from models import HUbMenuLevel


async def load_menu_tree(session: AsyncSession) -> Dict[int, List[int]]:
    stmt = select(HUbMenuLevel.id, HUbMenuLevel.parent_id)
    rows = (await session.execute(stmt)).all()

    tree: Dict[int, List[int]] = {}

    for row in rows:
        node_id = row.id
        parent_id = row.parent_id

        if parent_id not in tree:
            tree[parent_id] = []

        tree[parent_id].append(node_id)

    return tree


def collect_descendants(tree: Dict[int, List[int]], node_id: int, result: Set[int]):
    result.add(node_id)
    if node_id not in tree:
        return
    for child in tree[node_id]:
        collect_descendants(tree, child, result)


async def resolve_menu_levels_to_path_ids(selected_levels: List[int], session: AsyncSession) -> List[int]:
    if not selected_levels:
        return []

    tree = await load_menu_tree(session)

    result: Set[int] = set()

    for level_id in selected_levels:
        collect_descendants(tree, level_id, result)

    shuffled = random.sample(list(result), k=len(result))
    return shuffled


def build_cursor_response(rows: list[RowMapping], limit: int):
    if not rows:
        return None, False

    last_id = rows[-1]["id"]
    has_more = len(rows) == limit

    next_cursor = last_id if has_more else None

    return next_cursor, has_more
