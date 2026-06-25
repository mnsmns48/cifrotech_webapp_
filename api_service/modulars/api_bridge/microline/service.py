from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, delete, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.modulars.api_bridge.microline.client import MicrolineClient
from api_service.modulars.api_bridge.microline.helpers import normalize_product_brands, sync_product_brands, \
    build_vsl_products, collect_needed_origins, build_vsl_brands_map, sync_product_origins, get_default_reward_lines, \
    rebuild_parsing_lines
from api_service.modulars.api_bridge.microline.schemas import AddVendorApiSearch, VendorApiSearchResponse, \
    DeleteVendorApiSearch, VendorApiSearchDeleteResponse, ApiSearchVSLResponse, UpdateLinesFromApi
from api_service.modulars.api_bridge.token_services import AuthResult
from api_service.schemas import BrandModel, VSLScheme, VSLSchemeWithBrands, RewardRangeLineSchema
from models import Vendor, VendorApiSearch, VendorSearchLine, VendorApiSearchLineLink, ProductBrand, ProductOrigin, \
    ParsingLine
from models.vendor import VendorSearchLineBrandLink, RewardRange
from parsing.utils import cost_process


def normalize_dt(dt: datetime | None):
    if dt is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class MicrolineService:
    def __init__(self, auth_service, client: MicrolineClient):
        self.auth = auth_service
        self.client = client

    async def _get_vendor(self, vendor_id, session):
        vendor = await session.get(Vendor, vendor_id)
        if not vendor:
            raise HTTPException(404, "Vendors not found")
        return vendor

    async def _ensure_auth(self, vendor, session):
        result = await self.auth.ensure_valid_tokens(vendor, session)
        if result == AuthResult.NEED_LOGIN:
            raise HTTPException(401, "Authorization required")
        if result == AuthResult.INACTIVE:
            raise HTTPException(403, "Integration inactive")
        return result

    async def get_me(self, vendor_id, session):
        vendor = await self._get_vendor(vendor_id, session)
        await self._ensure_auth(vendor, session)
        return await self.client.get_me(vendor)

    async def get_contractors(self, vendor_id, session):
        vendor = await self._get_vendor(vendor_id, session)
        await self._ensure_auth(vendor, session)
        return await self.client.get_contractors(vendor)

    async def load_categories(self, vendor_id, session, parent_id=None):
        vendor = await self._get_vendor(vendor_id, session)
        await self._ensure_auth(vendor, session)
        return await self.client.get_categories(vendor, parent_id)

    async def get_products(self, vendor_id, session, contractor_id, delivery_location_id, category_id):
        vendor = await self._get_vendor(vendor_id, session)
        await self._ensure_auth(vendor, session)

        return await self.client.get_products(vendor,
                                              contractor_id=contractor_id,
                                              delivery_location_id=delivery_location_id,
                                              category_id=category_id)


class ApiBridgeService:
    @staticmethod
    async def bridge_add_vendor_api_search(payload: AddVendorApiSearch,
                                           session: AsyncSession) -> VendorApiSearchResponse:
        data = payload.model_dump(exclude_none=True)
        obj = VendorApiSearch(**data)
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return VendorApiSearchResponse(status="ok", id=obj.id, **data)

    @staticmethod
    async def bridge_delete_vendor_api_search(payload: DeleteVendorApiSearch,
                                              session: AsyncSession) -> VendorApiSearchDeleteResponse:
        stmt = (select(VendorApiSearch).where(VendorApiSearch.vendor_id == payload.vendor_id)
                .where(VendorApiSearch.category_id == payload.category_id))

        result = await session.execute(stmt)
        obj = result.scalar_one_or_none()

        if obj is None:
            return VendorApiSearchDeleteResponse(status="not_found", deleted_id=None, **payload.model_dump())

        await session.delete(obj)
        await session.commit()

        return VendorApiSearchDeleteResponse(status="ok", deleted_id=obj.id, **payload.model_dump())

    @staticmethod
    async def get_vendor_api_search_line_link(api_search_id: int, session: AsyncSession) -> ApiSearchVSLResponse:
        api_search = await session.get(VendorApiSearch, api_search_id)
        if api_search is None:
            return ApiSearchVSLResponse(status=False, all_VSL=[], linked_VSL=[])
        vendor_id = api_search.vendor_id
        stmt_all = select(VendorSearchLine).where(VendorSearchLine.vendor_id == vendor_id)
        rows_all = await session.execute(stmt_all)
        all_vsl = rows_all.scalars().all()
        stmt_linked = ((select(VendorSearchLine).join(VendorApiSearchLineLink,
                                                      VendorApiSearchLineLink.vsl_id == VendorSearchLine.id)
                        .where(VendorApiSearchLineLink.api_search_id == api_search_id))
                       .order_by(VendorSearchLine.dt_parsed.desc()))
        rows_linked = await session.execute(stmt_linked)
        linked_vsl = rows_linked.scalars().all()

        vsl_ids = list()
        for v in all_vsl:
            vsl_ids.append(v.id)

        stmt_brands = (select(VendorSearchLineBrandLink, ProductBrand).join(ProductBrand,
                                                                            ProductBrand.id == VendorSearchLineBrandLink.brand_id)
                       .where(VendorSearchLineBrandLink.vsl_id.in_(vsl_ids)))
        rows_brands = await session.execute(stmt_brands)
        brand_pairs = rows_brands.all()

        brand_map = dict()
        for link, brand in brand_pairs:
            vsl_id = link.vsl_id
            if vsl_id not in brand_map:
                brand_map[vsl_id] = list()
            brand_map[vsl_id].append(BrandModel.model_validate(brand))

        all_vsl_schemes = list()
        for v in all_vsl:
            base = VSLScheme.cls_validate(v)
            vsl_id = v.id
            brands = brand_map[vsl_id] if vsl_id in brand_map else None
            all_vsl_schemes.append(VSLSchemeWithBrands(**base, brands=brands))

        all_vsl_schemes.sort(
            key=lambda x: normalize_dt(getattr(x, "dt_parsed", None)),
            reverse=True)

        linked_vsl_schemes = list()
        for v in linked_vsl:
            base = VSLScheme.cls_validate(v)
            vsl_id = v.id
            brands = brand_map[vsl_id] if vsl_id in brand_map else None
            linked_vsl_schemes.append(VSLSchemeWithBrands(**base, brands=brands))

        status = False
        if len(linked_vsl_schemes) > 0:
            status = True

        return ApiSearchVSLResponse(status=status, all_VSL=all_vsl_schemes, linked_VSL=linked_vsl_schemes)

    @staticmethod
    async def update_parsing_line_data_from_api(payload: UpdateLinesFromApi, session: AsyncSession):
        normalize_product_brands(payload.raw_products)
        vsl_brands_map = build_vsl_brands_map(payload.linked_VSL)
        await sync_product_brands(session=session, raw_products=payload.raw_products, vsl_brands_map=vsl_brands_map,
                                  linked_vsl=payload.linked_VSL)
        vsl_products = build_vsl_products(payload.raw_products, payload.linked_VSL, vsl_brands_map)
        needed_origins = collect_needed_origins(vsl_products)

        if not needed_origins:
            return {"status": "ok", "message": "Нет подходящих продуктов"}

        deleted_origins = await sync_product_origins(session=session, needed_origins=needed_origins,
                                                     raw_products=payload.raw_products)

        reward_lines, reward_range_id = await get_default_reward_lines(session)

        total_inserted = await rebuild_parsing_lines(session=session,
                                                     linked_vsl=payload.linked_VSL,
                                                     vsl_products=vsl_products,
                                                     deleted_origins=deleted_origins,
                                                     reward_lines=reward_lines,
                                                     reward_range_id=reward_range_id)
        await session.commit()
        return {"status": "ok", "inserted": total_inserted}
