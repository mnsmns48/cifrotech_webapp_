import re
from typing import Dict

from api_service.modulars.formula.environment import env
from api_service.modulars.formula.filters import get_param
from api_service.s3_helper import get_url_from_s3
from api_service.schemas import SpecsParamScheme
from api_service.schemas.desc_builder import BlockResponse, ValueInfo, ProductDescription
from config import settings
from models import SpecPath


def render_blocks_for_product(prepared_lines: list[dict], paths_map: dict, info: dict) -> list[BlockResponse]:
    blocks: list[BlockResponse] = list()

    for idx, line in enumerate(prepared_lines, start=1):
        block = render_formula_description(line, paths_map, info)
        if not block:
            continue

        block.title = f"{idx}-row-block-short-specs"
        blocks.append(block)

    return blocks


def normalize_info(raw_info):
    if isinstance(raw_info, list):
        merged = {}
        for block in raw_info:
            if isinstance(block, dict):
                merged.update(block)
        return merged
    return raw_info or {}


def build_paths_map(path_rows: list[SpecPath]):
    paths_map = dict()
    for row in path_rows:
        category, param = row.path
        if row.title not in paths_map:
            paths_map[row.title] = {"icon": row.icon, "paths": [], "alias": row.alias, "in_filter": row.in_filter}
        paths_map[row.title]["paths"].append(SpecsParamScheme(category=category, param=param))

    return paths_map


def render_formula_description(prepared_line: dict, paths_map: dict, info: dict):
    values: Dict[str, ValueInfo] = {}
    has_non_empty_value = False
    first_icon = None

    for var in prepared_line["vars"]:
        if var not in paths_map:
            values[var] = ValueInfo(raw="", processed="", alias=None, in_filter=None)
            continue

        schemes = paths_map[var]["paths"]
        raw_value = str(get_param(info, schemes) or "")
        alias = paths_map[var].get("alias")
        in_filter = paths_map[var].get("in_filter")

        values[var] = ValueInfo(raw=raw_value, processed="", alias=alias, in_filter=in_filter)

        if raw_value:
            has_non_empty_value = True
            if first_icon is None:
                icon = paths_map[var].get("icon")
                if icon:
                    first_icon = get_url_from_s3(icon, settings.s3.utils_path)

    if not has_non_empty_value:
        return None

    rendered = prepared_line["template"].render(**{var: values[var].raw for var in prepared_line["vars"]}).strip()

    rendered = re.sub(r"^,+", "", rendered)
    rendered = re.sub(r",+$", "", rendered)
    rendered = re.sub(r"\s{2,}", " ", rendered).strip()

    for var in prepared_line["vars"]:
        raw = values[var].raw
        filters = prepared_line["filters"].get(var, [])
        processed = apply_filters(raw, filters)
        values[var].processed = processed

    return BlockResponse(title="", text=rendered, icon=first_icon, values=values)


def apply_filters(value: str, filters: list[tuple[str, list]]) -> str:
    if not value:
        return ""

    result = value

    for fname, args in filters:
        try:
            func = env.filters.get(fname)
            if not func:
                continue
            result = func(result, *args)

        except Exception:
            continue

    result = re.sub(r"\s{2,}", " ", str(result)).strip()
    return result


def prepare_formula_lines(lines: list[str]) -> list[dict]:
    prepared = list()
    block_pattern = r"{{\s*(.*?)\s*}}"

    for line in lines:
        blocks = re.findall(block_pattern, line)
        if not blocks:
            continue

        vars_list = list()
        filters_map = dict()

        for block in blocks:
            parts = [p.strip() for p in block.split("|")]

            var = parts[0]
            vars_list.append(var)

            filters = []
            for part in parts[1:]:
                m = re.match(r"(\w+)\s*\((.*)\)", part)
                if not m:
                    continue

                fname = m.group(1)
                args_raw = m.group(2).strip()

                args = list()
                if args_raw:
                    for arg in re.split(r"\s*,\s*", args_raw):
                        arg = arg.strip().strip('"').strip("'")
                        if arg.isdigit():
                            arg = int(arg)
                        args.append(arg)
                filters.append((fname, args))
            filters_map[var] = filters

        prepared.append({"vars": list(dict.fromkeys(vars_list)),
                         "filters": filters_map,
                         "template": env.from_string(line)})

    return prepared


def render_group(ids: list[int],
                 pf_map: dict[int, dict], paths_map: dict, lines: list[str]) -> dict[int, ProductDescription]:
    prepared_lines = prepare_formula_lines(lines)
    result: dict[int, ProductDescription] = dict()

    for pid in ids:
        info = pf_map.get(pid) or {}
        blocks = render_blocks_for_product(prepared_lines=prepared_lines, paths_map=paths_map, info=info)
        result[pid] = ProductDescription(blocks=blocks)

    return result


def group_by_type_source(meta_rows):
    groups = dict()
    for pid, type_id, source in meta_rows:
        groups.setdefault((type_id, source), []).append(pid)
    return groups
