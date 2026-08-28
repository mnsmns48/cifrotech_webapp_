import re
from typing import Dict

from jinja2 import TemplateSyntaxError, UndefinedError, TemplateRuntimeError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.modulars.formula.environment import env
from api_service.modulars.formula.filters import get_param
from api_service.schemas import GenerateDescriptionPayload, SpecsParamScheme, DescriptionResponse, DescriptionError, \
    DescriptionSuccess
from api_service.s3_helper import get_url_from_s3
from api_service.schemas.desc_builder import BlockResponse, ValueInfo, ProductDescription
from config import settings

from models import ProductFeaturesGlobal, SpecsComposer, SpecPath, ProductFeaturesLink


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
        select(SpecsComposer).where(SpecsComposer.type_id == type_id,
                                    SpecsComposer.source == source)
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
    paths_map = dict()
    for row in path_rows:
        category, param = row.path
        if row.title not in paths_map:
            paths_map[row.title] = {
                "icon": row.icon, "paths": [], "alias": row.alias, "in_filter": row.in_filter
            }
        paths_map[row.title]["paths"].append(SpecsParamScheme(category=category, param=param))

    return paths_map


def render_formula_description(prepared_line: dict, paths_map: dict, info: dict):
    values: Dict[str, ValueInfo] = {}
    has_non_empty_value = False
    first_icon = None

    # 1. Собираем raw и метаданные
    for var in prepared_line["vars"]:
        if var not in paths_map:
            values[var] = ValueInfo(raw="", processed="", alias=None, in_filter=None)
            continue

        schemes = paths_map[var]["paths"]
        raw_value = str(get_param(info, schemes) or "")

        alias = paths_map[var].get("alias")
        in_filter = paths_map[var].get("in_filter")

        values[var] = ValueInfo(
            raw=raw_value,
            processed="",  # заполним позже
            alias=alias,
            in_filter=in_filter
        )

        if raw_value:
            has_non_empty_value = True
            if first_icon is None:
                icon = paths_map[var].get("icon")
                if icon:
                    first_icon = get_url_from_s3(icon, settings.s3.utils_path)

    if not has_non_empty_value:
        return None

    # 2. Рендерим text — полная формула
    rendered = prepared_line["template"].render(
        **{var: values[var].raw for var in prepared_line["vars"]}
    ).strip()

    rendered = re.sub(r"^,+", "", rendered)
    rendered = re.sub(r",+$", "", rendered)
    rendered = re.sub(r"\s{2,}", " ", rendered).strip()

    # 3. processed = raw, пропущенный через фильтры
    for var in prepared_line["vars"]:
        raw = values[var].raw
        filters = prepared_line["filters"].get(var, [])
        processed = apply_filters(raw, filters)
        values[var].processed = processed

    return BlockResponse(
        text=rendered,
        icon=first_icon,
        values=values
    )


def apply_filters(value: str, filters: list[tuple[str, list]]) -> str:
    """
    Применяет фильтры Jinja вручную к одному значению.
    filters: [("cut_left", ["inches", 0]), ("replace", ["Hz", ""])]
    """

    if not value:
        return ""

    result = value

    for fname, args in filters:
        try:
            # фильтр должен существовать в env.filters
            func = env.filters.get(fname)
            if not func:
                continue

            # вызываем фильтр как обычную Python-функцию
            # Jinja-фильтры всегда принимают первым аргументом value
            result = func(result, *args)

        except Exception:
            # если фильтр упал — не ломаем весь пайплайн
            continue

    # финальная чистка
    result = re.sub(r"\s{2,}", " ", str(result)).strip()
    return result



def prepare_formula_lines(lines: list[str]) -> list[dict]:
    prepared = []

    # Находим все {{ ... }} блоки
    block_pattern = r"{{\s*(.*?)\s*}}"

    for line in lines:
        blocks = re.findall(block_pattern, line)
        if not blocks:
            continue

        vars_list = []
        filters_map = {}

        for block in blocks:
            # Пример блока:
            # "display_size | cut_left('inches', 0) | replace('Hz', '')"
            parts = [p.strip() for p in block.split("|")]

            var = parts[0]                     # первая часть — имя переменной
            vars_list.append(var)

            filters = []
            for part in parts[1:]:             # остальные части — фильтры
                # Пример part:
                # "cut_left('inches', 0)"
                m = re.match(r"(\w+)\s*\((.*)\)", part)
                if not m:
                    continue

                fname = m.group(1)
                args_raw = m.group(2).strip()

                # Разбираем аргументы максимально просто
                args = []
                if args_raw:
                    for arg in re.split(r"\s*,\s*", args_raw):
                        arg = arg.strip().strip('"').strip("'")
                        if arg.isdigit():
                            arg = int(arg)
                        args.append(arg)

                filters.append((fname, args))

            filters_map[var] = filters

        prepared.append({
            "vars": list(dict.fromkeys(vars_list)),
            "filters": filters_map,
            "template": env.from_string(line),
        })

    return prepared




def render_group(
        ids: list[int],
        pf_map: dict[int, dict],
        paths_map: dict,
        lines: list[str],
) -> dict[int, ProductDescription]:
    prepared_lines = prepare_formula_lines(lines)

    result: dict[int, ProductDescription] = {}

    for pid in ids:
        info = pf_map.get(pid) or {}
        blocks: list[BlockResponse] = []

        for line in prepared_lines:
            block = render_formula_description(line, paths_map, info)
            if block:
                blocks.append(block)

        result[pid] = ProductDescription(blocks=blocks)

    return result


async def generate_description_db(payload: GenerateDescriptionPayload, session: AsyncSession) -> DescriptionResponse:
    try:
        if payload.product_features_map:
            pf_map = payload.product_features_map

        elif payload.origins:
            stmt = select(ProductFeaturesLink.feature_id).where(
                ProductFeaturesLink.origin.in_(payload.origins)
            )
            result = await session.execute(stmt)
            feature_ids = [row[0] for row in result.all()]
            pf_map = {fid: None for fid in feature_ids}

        else:
            return DescriptionResponse(
                error=DescriptionError(error="No product_features_map or origins provided")
            )

        product_ids = list(pf_map.keys())

        await prepare_product_info_bulk(session, pf_map)

        meta_rows = await load_meta_bulk(session, product_ids)
        groups = group_by_type_source(meta_rows)

        final: dict[int, ProductDescription] = {}

        for (type_id, source), ids in groups.items():
            composer, paths_map, lines = await load_group_resources(session, type_id, source)

            if not composer or not paths_map or not lines:
                # нет формулы/путей → пустые блоки
                for pid in ids:
                    final[pid] = ProductDescription(blocks=[])
                continue

            prepared_lines = prepare_formula_lines(lines)

            for pid in ids:
                info = pf_map.get(pid) or {}
                blocks: list[BlockResponse] = []

                for line in prepared_lines:
                    block = render_formula_description(line, paths_map, info)
                    if block:
                        blocks.append(block)
                    print(block)
                final[pid] = ProductDescription(blocks=blocks)

        return DescriptionResponse(
            success=DescriptionSuccess(products=final)
        )

    except (TemplateSyntaxError, UndefinedError, TemplateRuntimeError) as e:
        return DescriptionResponse(
            error=DescriptionError(error="Template rendering failed", details=str(e))
        )
