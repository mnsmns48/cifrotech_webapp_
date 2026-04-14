from sqlalchemy import select
from sqlalchemy.orm import aliased

from api_service.schemas import ResolveFeatureModel, TypeModel, BrandModel, ComparableModel
from models import HUbStock, ParsingLine, ProductFeaturesLink, ProductType, ProductBrand, ProductFeaturesGlobal


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



def assemble_comparable_models(
    path_ids,
    hub_origins_by_path,
    parsing_origins_by_path,
    feature_id_by_origin,
    model_by_id
):
    result = []

    for pid in path_ids:
        parsing_origins = parsing_origins_by_path.get(pid, set())
        hub_origins = hub_origins_by_path.get(pid, set())

        origins = parsing_origins | hub_origins

        models_by_fid = {}

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
                continue

            models_by_fid[fid] = ResolveFeatureModel(
                id=fid,
                title=row["title"],
                info=row["info"],
                type_=TypeModel(id=row["type_id"], type=row["type_name"]),
                brand=BrandModel(id=row["brand_id"], brand=row["brand_name"]),
                in_parsing=in_parsing,
                in_hub=in_hub,
            )

        # сортировка без lambda
        models = list(models_by_fid.values())
        models.sort(key=lambda m: m.title.lower())

        result.append(ComparableModel(path_id=pid, models=models))

    return result

