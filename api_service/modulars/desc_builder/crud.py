import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.modulars.formula.filters import get_param
from api_service.schemas import GenerateDescriptionPayload, SpecsParamScheme
from app_utils import get_url_from_s3
from config import settings
from models import ProductFeaturesGlobal, SpecsComposer, SpecPath


def normalize_info(raw_info):
    if isinstance(raw_info, list):
        merged = {}
        for block in raw_info:
            if isinstance(block, dict):
                merged.update(block)
        return merged
    return raw_info or {}


async def prepare_product_info_bulk(session: AsyncSession, pf_map: dict[int, dict | None]):
    ids_to_load = [pid for pid, info in pf_map.items() if info is None]
    if not ids_to_load:
        return

    stmt = (
        select(
            ProductFeaturesGlobal.id,
            ProductFeaturesGlobal.info,
        )
        .where(ProductFeaturesGlobal.id.in_(ids_to_load))
    )
    result = await session.execute(stmt)

    for pid, info_raw in result.all():
        pf_map[pid] = normalize_info(info_raw)


async def load_meta_bulk(session: AsyncSession, product_ids: list[int]):
    stmt = (
        select(
            ProductFeaturesGlobal.id,
            ProductFeaturesGlobal.type_id,
            ProductFeaturesGlobal.source,
        )
        .where(ProductFeaturesGlobal.id.in_(product_ids))
    )
    result = await session.execute(stmt)
    return result.all()


def group_by_type_source(meta_rows):
    groups = {}
    for pid, type_id, source in meta_rows:
        groups.setdefault((type_id, source), []).append(pid)
    return groups


async def load_group_resources(session: AsyncSession, type_id: int, source: str):
    stmt_comp = (
        select(SpecsComposer)
        .where(
            SpecsComposer.type_id == type_id,
            SpecsComposer.source == source,
        )
        .options(selectinload(SpecsComposer.formula))
    )
    result = await session.execute(stmt_comp)
    composer = result.scalar_one_or_none()

    if not composer or not composer.formula:
        return None, None, None

    formula_text = composer.formula.formula or ""
    if not formula_text.strip():
        return None, None, None
    stmt_paths = (
        select(SpecPath)
        .where(
            SpecPath.formula_id == composer.formula_id,
            SpecPath.source == source,
        )
    )
    result = await session.execute(stmt_paths)
    path_rows = list(result.scalars().all())
    if not path_rows:
        return None, None, None
    paths_map = build_paths_map(path_rows)
    lines = [line.strip() for line in formula_text.split("\n") if line.strip()]

    return composer, paths_map, lines


def build_paths_map(path_rows: list[SpecPath]):
    paths_map = {}

    for row in path_rows:
        category, param = row.path
        if row.title not in paths_map:
            paths_map[row.title] = {
                "icon": row.icon,
                "paths": [],
            }
        paths_map[row.title]["paths"].append(
            SpecsParamScheme(category=category, param=param)
        )

    return paths_map


def render_formula_line(line: str, paths_map: dict, info: dict):
    vars_in_line = re.findall(r"([A-Za-z0-9_]+)_paths", line)

    if not vars_in_line:
        return None

    block_values = {}
    block_icon = None
    block_title = None

    for var in vars_in_line:
        if var not in paths_map:
            continue

        schemes = paths_map[var]["paths"]
        value = get_param(info, schemes)

        if not value:
            continue

        block_values[var] = value

        if block_icon is None:
            icon = paths_map[var]["icon"]
            if icon:
                block_icon = get_url_from_s3(filename=icon, path=settings.s3.utils_path)

        if block_title is None:
            block_title = var

    if not block_values:
        return None

    rendered = line
    for var, value in block_values.items():
        rendered = rendered.replace(
            f"{{{{ get_param(info, {var}_paths) }}}}",
            value
        )

    return {
        "title": block_title,
        "icon": block_icon,
        "text": rendered,
        "values": block_values,
    }


def render_group(ids: list[int], pf_map: dict[int, dict], paths_map, lines):
    result = dict()
    for pid in ids:
        info = pf_map[pid]
        blocks = list()
        for line in lines:
            block = render_formula_line(line, paths_map, info)
            if block:
                blocks.append(block)
        result[pid] = {"blocks": blocks}

    return result


def assemble_result(group_results: list[dict[int, dict]]):
    final = {}
    for group in group_results:
        final.update(group)
    return final


async def generate_description_db(payload: GenerateDescriptionPayload, session: AsyncSession):
    pf_map = payload.product_features_map
    product_ids = list(pf_map.keys())
    await prepare_product_info_bulk(session, pf_map)
    meta_rows = await load_meta_bulk(session, product_ids)
    groups = group_by_type_source(meta_rows)

    group_results = list()
    for (type_id, source), ids in groups.items():
        composer, paths_map, lines = await load_group_resources(session, type_id, source)
        if not composer:
            group_results.append({pid: {"blocks": []} for pid in ids})
            continue
        group_results.append(render_group(ids, pf_map, paths_map, lines))
    return assemble_result(group_results)
