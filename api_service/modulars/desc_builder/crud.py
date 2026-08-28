from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.modulars.desc_builder.logic import normalize_info, build_paths_map

from models import ProductFeaturesGlobal, SpecsComposer, SpecPath


async def prepare_product_info_bulk(session: AsyncSession, pf_map: dict[int, dict | None]):
    ids_to_load = [pid for pid, info in pf_map.items() if info is None]
    if not ids_to_load:
        return

    stmt = select(ProductFeaturesGlobal.id, ProductFeaturesGlobal.info).where(ProductFeaturesGlobal.id.in_(ids_to_load))
    result = await session.execute(stmt)

    for pid, info_raw in result.all():
        pf_map[pid] = normalize_info(info_raw)


async def load_meta_bulk(session: AsyncSession, product_ids: list[int]):
    stmt = (select(ProductFeaturesGlobal.id, ProductFeaturesGlobal.type_id, ProductFeaturesGlobal.source)
            .where(ProductFeaturesGlobal.id.in_(product_ids)))
    result = await session.execute(stmt)
    return result.all()


async def load_group_resources(session: AsyncSession, type_id: int, source: str):
    stmt_comp = (select(SpecsComposer).where(SpecsComposer.type_id == type_id,
                                             SpecsComposer.source == source)
                 .options(selectinload(SpecsComposer.formula)))
    result = await session.execute(stmt_comp)
    composer = result.scalar_one_or_none()

    if not composer or not composer.formula:
        return None, None, None

    formula_text = composer.formula.formula or ""
    if not formula_text.strip():
        return None, None, None

    stmt_paths = (select(SpecPath).where(SpecPath.formula_id == composer.formula_id,
                                         SpecPath.source == source))
    result = await session.execute(stmt_paths)
    path_rows = list(result.scalars().all())
    if not path_rows:
        return None, None, None
    paths_map = build_paths_map(path_rows)
    lines = [line.strip() for line in formula_text.split("\n") if line.strip()]
    return composer, paths_map, lines
