from typing import Dict, List, Set, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_v3.schemas import HubLevelSchemeV3
from api_v3.slug import slugify
from cache.manager import CacheManager
from cache.keys.base import build_key
from cache.settings import cache_ttl
from models import HUbMenuLevel

MENU_LEVELS_CACHE_KEY = build_key("menu", "levels")
MENU_TREE_CACHE_KEY = build_key("menu", "tree")


class MenuTree:
    def __init__(self, session: AsyncSession, cache: Optional[CacheManager] = None):
        self.session = session
        self.cache = cache

    async def _load_tree_from_db(self) -> Dict[int, List[int]]:
        stmt = select(HUbMenuLevel.id, HUbMenuLevel.parent_id)
        rows = (await self.session.execute(stmt)).all()

        tree: Dict[int, List[int]] = dict()
        for row in rows:
            tree.setdefault(row.parent_id, []).append(row.id)

        return tree

    async def load_tree_rt(self) -> Dict[int, List[int]]:
        return await self._load_tree_from_db()

    async def load_tree_cached(self) -> Dict[int, List[int]]:
        if self.cache is None:
            return await self._load_tree_from_db()

        tree = await self.cache.get(MENU_TREE_CACHE_KEY)
        if tree is not None:
            return {int(k): [int(x) for x in v] for k, v in tree.items()}

        tree = await self._load_tree_from_db()
        await self.cache.set(MENU_TREE_CACHE_KEY, tree, ttl=cache_ttl.menu)
        return tree

    async def load_levels_cached(self) -> List[HubLevelSchemeV3]:
        if self.cache is not None:
            cached = await self.cache.get(MENU_LEVELS_CACHE_KEY)
            if cached is not None:
                return [HubLevelSchemeV3(**lvl) for lvl in cached]

        stmt = select(HUbMenuLevel.id, HUbMenuLevel.sort_order,
                      HUbMenuLevel.label, HUbMenuLevel.icon, HUbMenuLevel.parent_id)

        rows = (await self.session.execute(stmt)).mappings().all()

        levels: List[HubLevelSchemeV3] = list()
        for row in rows:
            d = dict(row)
            d["slug"] = slugify(d["label"])
            d["depth"] = 0
            levels.append(HubLevelSchemeV3(**d))

        if self.cache is not None:
            await self.cache.set(MENU_LEVELS_CACHE_KEY, [lvl.model_dump() for lvl in levels], ttl=cache_ttl.menu)

        return levels

    def collect_descendants(self, tree: Dict[int, List[int]], node_id: int) -> Set[int]:
        result = {node_id}
        for child in tree.get(node_id, []):
            result.update(self.collect_descendants(tree, child))
        return result

    async def resolve_menu_levels_to_path_ids_rt(self, menu_levels: List[int]) -> List[int]:
        if not menu_levels:
            return []

        tree = await self.load_tree_rt()
        result: Set[int] = set()

        for level_id in menu_levels:
            result.update(self.collect_descendants(tree, level_id))

        return list(result)

    async def resolve_slug_to_category(self, slug_path: List[str]) -> Optional[HubLevelSchemeV3]:
        levels = await self.load_levels_cached()
        current_parent = 1
        current_level = None
        for slug in slug_path:
            for lvl in levels:
                if lvl.slug == slug and lvl.parent_id == current_parent:
                    current_level = lvl
                    current_parent = lvl.id
                    break

        return current_level

    async def build_breadcrumbs(self, category_id: int) -> List[HubLevelSchemeV3]:
        levels = await self.load_levels_cached()
        id_map = {lvl.id: lvl for lvl in levels}

        breadcrumbs = list()
        current = id_map.get(category_id)

        while current:
            breadcrumbs.append(current)
            current = id_map.get(current.parent_id)

        return list(reversed(breadcrumbs))

    async def resolve_slug_to_category_and_path_ids(self, slug_path: List[str]):
        category = await self.resolve_slug_to_category(slug_path)
        if category is None:
            return None, [], []

        breadcrumbs = await self.build_breadcrumbs(category.id)
        tree = await self.load_tree_cached()
        path_ids = list(self.collect_descendants(tree, category.id))

        return category, breadcrumbs, path_ids
