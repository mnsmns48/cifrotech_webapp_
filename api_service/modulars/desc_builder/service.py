from typing import List, Dict, Tuple

from fastapi import HTTPException
from redis.asyncio import Redis

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.modulars.desc_builder.crud import generate_description_db
from api_service.schemas import FormulaIdObj, FormulaEntityTypeScheme, GenerateDescriptionPayload, \
    FetchComposerResponse, TypeModel, FormulaResponse
from api_service.schemas.desc_builder import SpecsComposerExpandedScheme, SpecsPathRequest, SpecPathResponse, \
    CreateSpecsComposer, SaveSpecsComposer, SpecsComposerResponse, UpdateComposer, CreateSpecPath, UpdateSpecPath, \
    DescriptionResponse, BlockResponse, ProductDescription
from api_service.s3_helper import get_url_from_s3
from cache import CacheManager
from cache.keys.features import short_specs_key
from cache.settings import cache_ttl
from config import settings
from models import DescBuilderFormulaLink, SpecsComposer, FormulaExpression, SpecPath, ProductType, \
    ProductFeaturesGlobal, ProductFeaturesLink


class DescBuilder:
    @staticmethod
    async def fetch_formula_link(session):
        stmt = select(DescBuilderFormulaLink).limit(1)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return {"exists": False, "entity_type": None}
        await session.refresh(row, ["entity_type"])
        return {"exists": True, "entity_type": FormulaEntityTypeScheme.model_validate(row.entity_type)}

    @staticmethod
    async def update_formula_link(formula: FormulaIdObj, session: AsyncSession):
        stmt = select(DescBuilderFormulaLink).limit(1)
        result = await session.execute(stmt)
        link = result.scalar_one_or_none()

        if link is None:
            new_link = DescBuilderFormulaLink(entity_type_id=formula.id)
            session.add(new_link)
            await session.commit()
            await session.refresh(new_link)
            return new_link

        link.entity_type_id = formula.id
        await session.commit()
        await session.refresh(link)
        return link

    @staticmethod
    async def generate_description(payload: GenerateDescriptionPayload, session: AsyncSession) -> DescriptionResponse:
        return await generate_description_db(payload, session)

    @staticmethod
    async def fetch_composer(formula_entity_type_id: int, session: AsyncSession):
        stmt_composers = (select(SpecsComposer).join(SpecsComposer.formula)
                          .options(
            selectinload(SpecsComposer.formula).selectinload(FormulaExpression.entity_type),
            selectinload(SpecsComposer.type),
        ).where(FormulaExpression.entity_type_id == formula_entity_type_id))
        composers = (await session.execute(stmt_composers)).scalars().all()
        composer_items = list()
        for comp in composers:
            composer_items.append(
                SpecsComposerExpandedScheme(id=comp.id, type=TypeModel(id=comp.type.id, type=comp.type.type),
                                            source=comp.source,
                                            formula=FormulaResponse.model_validate(comp.formula)))
        return FetchComposerResponse(entity_type_id=formula_entity_type_id,
                                     composers=composer_items)

    @staticmethod
    async def fetch_spec_path(payload: SpecsPathRequest, session: AsyncSession) -> List[SpecPathResponse]:
        stmt = (select(SpecPath).where(and_(SpecPath.formula_id == payload.formula_id),
                                       (SpecPath.source == payload.source)).order_by(SpecPath.id))
        rows = (await session.execute(stmt)).scalars().all()
        return [
            SpecPathResponse(id=row.id, title=row.title, path=row.path, alias=row.alias, in_filter=row.in_filter,
                             icon=get_url_from_s3(filename=row.icon or "no_photo.png", path=settings.s3.utils_path))
            for row in rows
        ]

    @staticmethod
    async def create_new_composer(formula_entity_type_id: int, session) -> CreateSpecsComposer:
        types_query = await session.execute(select(ProductType))
        types = types_query.scalars().all()
        sources_query = await session.execute(
            select(ProductFeaturesGlobal.source)
            .where(ProductFeaturesGlobal.source.isnot(None))
            .distinct())
        sources = [row[0] for row in sources_query.all()]
        formulas_query = await session.execute(
            select(FormulaExpression)
            .options(selectinload(FormulaExpression.entity_type))
            .where(FormulaExpression.entity_type_id == formula_entity_type_id)
            .order_by(FormulaExpression.name)
        )
        formulas = formulas_query.scalars().all()
        return CreateSpecsComposer(types=types, sources=sources, formulas=formulas)

    @staticmethod
    async def save_new_composer(payload: SaveSpecsComposer, session: AsyncSession) -> SpecsComposerResponse:
        new_obj = SpecsComposer(type_id=payload.type_id, source=payload.source, formula_id=payload.formula_id)
        session.add(new_obj)
        await session.commit()
        await session.refresh(new_obj)
        return SpecsComposerResponse.model_validate(new_obj)

    @staticmethod
    async def update_composer(payload: UpdateComposer, session: AsyncSession) -> SpecsComposerResponse:
        composer = await session.get(SpecsComposer, payload.id)
        if not composer:
            raise HTTPException(status_code=404, detail="Composer not found")
        changed = False
        for field in ("type_id", "source", "formula_id"):
            new_value = getattr(payload, field)
            if getattr(composer, field) != new_value:
                setattr(composer, field, new_value)
                changed = True
        if changed:
            await session.commit()
            await session.refresh(composer)
        return SpecsComposerResponse.model_validate(composer)

    @staticmethod
    async def delete_composer(composer_id: int, session: AsyncSession):
        composer = await session.get(SpecsComposer, composer_id)
        if not composer:
            raise HTTPException(status_code=404, detail="Composer not found")
        await session.delete(composer)
        await session.commit()
        return {"status": "deleted", "id": composer_id}

    @staticmethod
    async def create_spec_path(payload: CreateSpecPath, session: AsyncSession):
        spec = SpecPath(title=payload.title,
                        icon=None,
                        path=payload.path,
                        formula_id=payload.formula_id,
                        source=payload.source,
                        alias=payload.alias,
                        in_filter=payload.in_filter)
        session.add(spec)
        await session.commit()
        await session.refresh(spec)
        return spec

    @staticmethod
    async def update_spec_path(payload: UpdateSpecPath, session: AsyncSession) -> SpecPath:
        spec = await session.get(SpecPath, payload.id)

        if not spec:
            raise HTTPException(404, "SpecPath not found")

        updates = {"title": payload.title,
                   "path": payload.path,
                   "alias": payload.alias,
                   "in_filter": payload.in_filter}

        changed = False

        for field, value in updates.items():
            if getattr(spec, field) != value:
                setattr(spec, field, value)
                changed = True

        if changed:
            await session.commit()
            await session.refresh(spec)

        return spec

    @staticmethod
    async def delete_spec_path(spec_path_id: int, session: AsyncSession):
        spec = await session.get(SpecPath, spec_path_id)
        if not spec:
            raise HTTPException(404, "SpecPath not found")
        await session.delete(spec)
        await session.commit()
        return {"status": "deleted", "id": spec_path_id}

    @staticmethod
    async def get_short_specs_bulk(feature_ids: List[int], session: AsyncSession,
                                   cache: CacheManager) -> Dict[int, List[BlockResponse]]:

        if not feature_ids:
            return {}

        cached_map, missing_ids = await DescBuilder.fetch_short_specs_from_cache_bulk(feature_ids, cache)
        if not missing_ids:
            return DescBuilder._convert_to_block_response_bulk(cached_map)
        new_map = await DescBuilder.generate_short_specs_for_feature_ids(missing_ids, session)
        await DescBuilder.cache_short_specs_bulk(new_map, cache)
        full_map = {**cached_map, **new_map}
        return DescBuilder._convert_to_block_response_bulk(full_map)

    @staticmethod
    async def get_short_specs_by_origins(origins: List[str], session: AsyncSession,
                                         redis: Redis) -> Dict[str, List[BlockResponse]]:
        if not origins:
            return {}

        origin_map = await DescBuilder.resolve_feature_ids_by_origins(origins, session)
        feature_ids = list(origin_map.values())

        specs_map = await DescBuilder.get_short_specs_bulk(feature_ids, session, redis)
        result: Dict[str, List[BlockResponse]] = dict()
        for origin, fid in origin_map.items():
            result[origin] = specs_map.get(fid, [])

        return result

    @staticmethod
    async def resolve_feature_ids_by_origins(origins: List[str], session: AsyncSession) -> Dict[str, int]:

        if not origins:
            return {}

        stmt = (select(ProductFeaturesLink.origin, ProductFeaturesLink.feature_id)
                .where(ProductFeaturesLink.origin.in_(origins)))

        rows = await session.execute(stmt)
        rows = rows.all()
        return {origin: fid for origin, fid in rows}

    @staticmethod
    async def fetch_short_specs_from_cache_bulk(feature_ids: List[int],
                                                cache: CacheManager) -> Tuple[Dict[int, ProductDescription], List[int]]:
        keys = [short_specs_key(fid) for fid in feature_ids]
        raw_map = await cache.mget(keys, model=ProductDescription)
        cached: Dict[int, ProductDescription] = {}
        missing: List[int] = list()

        for fid, key in zip(feature_ids, keys):
            obj = raw_map.get(key)
            if obj is None:
                missing.append(fid)
            else:
                cached[fid] = obj

        return cached, missing

    @staticmethod
    async def cache_short_specs_bulk(specs_map: Dict[int, ProductDescription], cache: CacheManager) -> None:
        if not specs_map:
            return

        mapping = {short_specs_key(fid): desc for fid, desc in specs_map.items()}
        await cache.mset(mapping, ttl=cache_ttl.short_specs)

    @staticmethod
    async def generate_short_specs_for_feature_ids(feature_ids: List[int],
                                                   session: AsyncSession) -> Dict[int, ProductDescription]:

        if not feature_ids:
            return {}

        pf_map = {fid: None for fid in feature_ids}
        payload = GenerateDescriptionPayload(product_features_map=pf_map)
        raw_response = await DescBuilder.generate_description(payload, session)
        desc_response = DescriptionResponse.model_validate(raw_response)

        if desc_response.error:
            return {}

        return desc_response.success.products

    @staticmethod
    def _convert_to_block_response_bulk(specs_map: Dict[int, ProductDescription]) -> Dict[int, List[BlockResponse]]:

        result: Dict[int, List[BlockResponse]] = dict()

        for fid, product_desc in specs_map.items():
            blocks = list()
            for block in product_desc.blocks:
                blocks.append(BlockResponse(**block.dict()))
            result[fid] = blocks

        return result
