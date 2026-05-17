from datetime import datetime
from typing import List

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.analytics.crud import load_market_settings, update_market_setting
from api_service.modulars.analytics.origin_analyzer import OriginAnalyzer
from api_service.modulars.price_sync.crud import fetch_raw_origins_db, fetch_leaf_routes, collect_price_sync_paths, \
    hubstock_origins_map_by_path_ids, load_parsing_origins_map, load_origin_feature_map, load_unique_models_by_origins, \
    load_origins_attrs_map
from api_service.modulars.price_sync.func import normalize_route, filter_unique_origins_by_attrs
from api_service.s3_helper import load_images_for_origins
from api_service.schemas import PathIdRequest, PriceSyncPickedPath, SyncPathWOrigins, ModelForApprove, \
    AttributeKeyValueSchema, ImageWithPreview, ProductMarketSettingsSchema, HubRoutes, SyncPathWMarket, SyncPathWModels, \
    UpdateMarketSettingsRequest
from models import HUbStock


class PriceSync:
    @staticmethod
    async def start_sync_process(payload: PathIdRequest, session: AsyncSession) -> List[PriceSyncPickedPath]:
        leaf_routes: List[HubRoutes] = await fetch_leaf_routes(session, [payload.path_id])
        return await collect_price_sync_paths(session, leaf_routes)

    @staticmethod
    async def fetch_raw_origins(payload: List[PriceSyncPickedPath], session: AsyncSession) -> List[SyncPathWOrigins]:
        return await fetch_raw_origins_db(payload, session)

    @staticmethod
    async def resolve_models_sync(payload: List[PriceSyncPickedPath], session: AsyncSession) -> List[SyncPathWModels]:
        for line in payload:
            line.route = normalize_route(line.route)

        payload.sort(key=lambda item: [lvl.sort_order for lvl in item.route])

        path_ids = [p.path_id for p in payload]

        hubstock_origin_map: dict[int, set[int]] = await hubstock_origins_map_by_path_ids(path_ids, session)
        parsing_origin_map: dict[int, set[int]] = await load_parsing_origins_map(payload, session)

        hubstock_origins = {o for s in hubstock_origin_map.values() for o in s}
        parsing_origins = {o for s in parsing_origin_map.values() for o in s}

        origin_feature_map: dict[int, dict[str, int | bool]] = await load_origin_feature_map(
            hubstock_origins, parsing_origins, session)

        models_list: list[ModelForApprove] = await load_unique_models_by_origins(origin_feature_map, session)

        model_by_feature_id = {m.id: m for m in models_list}
        all_origin_ids = {o.origin for m in models_list for o in m.origins}

        attrs_map = await load_origins_attrs_map(all_origin_ids, session)
        result: List[SyncPathWModels] = list()

        for p in payload:
            path_id = p.path_id
            hubstock_for_path = hubstock_origin_map.get(path_id, set())
            parsing_for_path = parsing_origin_map.get(path_id, set())
            origins_for_path = hubstock_for_path | parsing_for_path

            if not origins_for_path:
                continue

            feature_to_origins: dict[int, list[int]] = dict()

            for origin in origins_for_path:
                feature_info = origin_feature_map.get(origin)
                if not feature_info:
                    continue
                feature_id = feature_info["feature_id"]
                feature_to_origins.setdefault(feature_id, []).append(origin)

            models_for_path: list[ModelForApprove] = list()

            for feature_id, origins_subset in feature_to_origins.items():
                model = model_by_feature_id.get(feature_id)
                if not model:
                    continue

                filtered_origins = [o for o in model.origins if o.origin in origins_subset]
                if not filtered_origins:
                    continue

                in_hub = any(origin_id in hubstock_for_path for origin_id in origins_subset)

                model_copy = ModelForApprove(id=model.id,
                                             title=model.title,
                                             info=model.info,
                                             source=model.source,
                                             type_=model.type_,
                                             brand=model.brand,
                                             in_hub=in_hub,
                                             origins=filtered_origins)
                models_for_path.append(model_copy)

            if not models_for_path:
                continue

            filter_unique_origins_by_attrs(models_for_path, attrs_map)
            models_for_path.sort(
                key=lambda m: min((o.input_price or float("inf")) for o in m.origins)
            )

            result.append(
                SyncPathWModels(path_id=path_id, route=p.route, models=models_for_path)
            )

        return result

    @staticmethod
    async def approve_origins_for_update(payload: list[SyncPathWModels],
                                         session: AsyncSession,
                                         s3_client) -> list[SyncPathWMarket]:
        path_ids = {path_item.path_id for path_item in payload}
        origin_ids: set[int] = {item.origin
                                for path_item in payload
                                for model in path_item.models
                                for item in model.origins}
        attrs_map: dict[int, list[AttributeKeyValueSchema]] = await load_origins_attrs_map(origin_ids, session)
        images_map: dict[int, list[ImageWithPreview]] = await load_images_for_origins(session, s3_client, origin_ids)
        market_settings: list[ProductMarketSettingsSchema] = await load_market_settings(session, path_ids)
        market_settings_map = {s.path_id: s for s in market_settings}
        analyzer = OriginAnalyzer(session, market_settings_map)
        await analyzer.load()
        result: list[SyncPathWMarket] = list()
        for line in payload:
            market = market_settings_map.get(line.path_id) or ProductMarketSettingsSchema(id=0,
                                                                                          path_id=line.path_id,
                                                                                          market_variance_scale=5.0,
                                                                                          market_variance_exponent=1.1)
            for model in line.models:
                for origin in model.origins:
                    origin.attrs = attrs_map.get(origin.origin, [])
                    origin.pics = images_map.get(origin.origin, [])
                analyzer.analyze_model(model, line.path_id)
            result.append(
                SyncPathWMarket(
                    path_id=line.path_id,
                    route=line.route,
                    models=line.models,
                    market=market
                )
            )
        return result

    @staticmethod
    async def update_market_param(payload: UpdateMarketSettingsRequest, session: AsyncSession) -> List[SyncPathWMarket]:
        updated_market = await update_market_setting(payload, session)
        market_settings_map = {payload.path_id: updated_market}
        analyzer = OriginAnalyzer(session, market_settings_map)
        await analyzer.load()
        for model in payload.models:
            analyzer.analyze_model(model, payload.path_id)
        return [SyncPathWMarket(path_id=payload.path_id,
                                route=payload.route,
                                models=payload.models,
                                market=updated_market)]

    @staticmethod
    async def update_origins_in_hubstock(payload: SyncPathWModels, session: AsyncSession):
        await session.execute(delete(HUbStock).where(HUbStock.path_id == payload.path_id))
        rows = list()
        for model in payload.models:
            for origin in model.origins:
                rows.append({"origin": origin.origin,
                             "path_id": payload.path_id,
                             "vsl_id": origin.vsl_id,
                             "input_price": origin.input_price,
                             "output_price": origin.output_price,
                             "warranty": origin.warranty,
                             "profit_range_id": origin.profit_range_id,
                             "updated_at": datetime.now()})
        await session.execute(insert(HUbStock), rows)
        await session.commit()
        return {"updated": len(rows)}
