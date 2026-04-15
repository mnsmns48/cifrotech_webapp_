from sqlalchemy import select, func
from sqlalchemy.orm import aliased

from api_service.schemas import ResolveFeatureModel, TypeModel, BrandModel, ComparableModel, ConcurrentAvailable

from models import HUbStock, ParsingLine, ProductFeaturesLink, ProductType, ProductBrand, ProductFeaturesGlobal, \
    ProductOrigin, AttributeOriginValue


async def load_hubstock_origins_by_path_ids(path_ids, session):
    rows = (
        await session.execute(
            select(HUbStock.path_id, HUbStock.origin, HUbStock.vsl_id)
            .where(HUbStock.path_id.in_(path_ids))
        )
    ).mappings().all()

    hub_origins_by_path = {}
    vsl_ids_by_path = {}
    vsl_to_paths = {}

    for row in rows:
        pid = row["path_id"]
        origin = row["origin"]
        vsl = row["vsl_id"]

        hub_origins_by_path.setdefault(pid, set()).add(origin)
        vsl_ids_by_path.setdefault(pid, set()).add(vsl)
        vsl_to_paths.setdefault(vsl, set()).add(pid)

    return hub_origins_by_path, vsl_ids_by_path, vsl_to_paths


async def load_parsing_origins(vsl_to_paths, path_ids, session):
    parsing_origins_by_path = {pid: set() for pid in path_ids}

    all_vsl_ids = set(vsl_to_paths.keys())
    if not all_vsl_ids:
        return parsing_origins_by_path

    rows = (
        await session.execute(
            select(ParsingLine.vsl_id, ParsingLine.origin)
            .where(ParsingLine.vsl_id.in_(all_vsl_ids))
        )
    ).mappings().all()

    for row in rows:
        vsl = row["vsl_id"]
        origin = row["origin"]

        for pid in vsl_to_paths.get(vsl, []):
            parsing_origins_by_path[pid].add(origin)

    return parsing_origins_by_path


async def load_feature_ids(all_origins, session):
    rows = (
        await session.execute(
            select(ProductFeaturesLink.origin, ProductFeaturesLink.feature_id)
            .where(ProductFeaturesLink.origin.in_(all_origins))
        )
    ).mappings().all()

    feature_id_by_origin = {}
    for row in rows:
        feature_id_by_origin[row["origin"]] = row["feature_id"]

    return feature_id_by_origin


async def load_models(all_feature_ids, session):
    type_alias = aliased(ProductType)
    brand_alias = aliased(ProductBrand)

    rows = (
        await session.execute(
            select(
                ProductFeaturesGlobal.id,
                ProductFeaturesGlobal.title,
                ProductFeaturesGlobal.info,
                type_alias.id.label("type_id"),
                type_alias.type.label("type_name"),
                brand_alias.id.label("brand_id"),
                brand_alias.brand.label("brand_name"),
            )
            .join(type_alias, type_alias.id == ProductFeaturesGlobal.type_id)
            .join(brand_alias, brand_alias.id == ProductFeaturesGlobal.brand_id)
            .where(ProductFeaturesGlobal.id.in_(all_feature_ids))
            .order_by(ProductFeaturesGlobal.title)
        )
    ).mappings().all()

    model_by_id = {}
    for row in rows:
        model_by_id[row["id"]] = row

    return model_by_id


async def load_unique_models_by_origin(origins: set[int], session) -> dict[int, ConcurrentAvailable]:
    if not origins:
        return {}

    rows = ((await session.execute(select(ParsingLine.origin,
                                          func.min(ParsingLine.input_price).label("input_price"),
                                          func.min(ParsingLine.output_price).label("output_price"),
                                          ProductOrigin.title,
                                          ProductFeaturesGlobal.id.label("model_id"),
                                          func.array_agg(AttributeOriginValue.attr_value_id.distinct()).label("attrs"))
                                   .join(ProductOrigin, ProductOrigin.origin == ParsingLine.origin)
                                   .join(ProductFeaturesLink, ProductFeaturesLink.origin == ParsingLine.origin)
                                   .join(ProductFeaturesGlobal,
                                         ProductFeaturesGlobal.id == ProductFeaturesLink.feature_id)
                                   .outerjoin(AttributeOriginValue,
                                              AttributeOriginValue.origin_id == ParsingLine.origin)
                                   .where(ParsingLine.origin.in_(origins))
                                   .group_by(ParsingLine.origin, ProductOrigin.title, ProductFeaturesGlobal.id)))
            .mappings().all())

    normalized = list()
    for r in rows:
        normalized.append(dict(r, attrs=tuple(sorted(r["attrs"] or []))))

    normalized = sorted(normalized, key=lambda r: (r["model_id"], r["attrs"]))

    groups = dict()
    for row in normalized:
        key = (row["model_id"], row["attrs"])
        if key not in groups:
            groups[key] = []
        groups[key].append(row)

    model_available = dict()

    for (model_id, attrs), items in groups.items():
        best = min(items, key=lambda r: r["input_price"])

        if model_id not in model_available:
            model_available[model_id] = []

        model_available[model_id].append(
            ConcurrentAvailable(origin=best["origin"],
                                title=best["title"],
                                input_price=best["input_price"],
                                output_price=best["output_price"]))

    for model_id in model_available:
        model_available[model_id] = sorted(model_available[model_id], key=lambda x: x.input_price)

    unique_by_origin = dict()

    for model_id, items in model_available.items():
        for item in items:
            unique_by_origin[item.origin] = item

    return unique_by_origin


def assemble_comparable_models(path_ids,
                               hub_origins_by_path,
                               parsing_origins_by_path,
                               feature_id_by_origin,
                               model_by_id,
                               unique_models_by_origin):
    result = list()

    for pid in path_ids:
        parsing_origins = parsing_origins_by_path.get(pid, set())
        hub_origins = hub_origins_by_path.get(pid, set())

        origins = parsing_origins | hub_origins

        models_by_fid = dict()

        for origin in origins:
            fid = feature_id_by_origin.get(origin)
            if not fid:
                continue

            row = model_by_id.get(fid)
            if not row:
                continue

            in_parsing = origin in parsing_origins
            in_hub = origin in hub_origins

            if fid in models_by_fid:
                m = models_by_fid[fid]
                m.in_parsing = m.in_parsing or in_parsing
                m.in_hub = m.in_hub or in_hub
            else:
                m = ResolveFeatureModel(
                    id=fid,
                    title=row["title"],
                    info=row["info"],
                    type_=TypeModel(id=row["type_id"], type=row["type_name"]),
                    brand=BrandModel(id=row["brand_id"], brand=row["brand_name"]),
                    in_parsing=in_parsing,
                    in_hub=in_hub,
                    available=[],
                )
                models_by_fid[fid] = m

            available_item = unique_models_by_origin.get(origin)
            if available_item:
                m.available.append(available_item)

        models = list(models_by_fid.values())
        models.sort(key=lambda x: x.title.lower())

        result.append(ComparableModel(path_id=pid, models=models))

    return result
