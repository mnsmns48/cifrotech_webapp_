from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, delete, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.modulars.api_bridge.microline.client import MicrolineClient
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
        for p in payload.raw_products:
            if p.brand:
                p.brand = p.brand.lower()

        vsl_brands_map = {vsl.id: {b.brand for b in (vsl.brands or [])} for vsl in payload.linked_VSL}
        vsl_products = defaultdict(list)

        for vsl in payload.linked_VSL:
            allowed = vsl_brands_map[vsl.id]
            for p in payload.raw_products:
                if p.brand and p.brand in allowed:
                    vsl_products[vsl.id].append(p)

        needed_origins = {int(p.productCode) for plist in vsl_products.values() for p in plist if p.productCode}

        if not needed_origins:
            return {"status": "ok", "message": "Нет подходящих продуктов"}

        existing_origins = (
            await session.execute(select(ProductOrigin)
                                  .where(ProductOrigin.origin.in_(needed_origins)))).scalars().all()

        origin_map = {o.origin: o for o in existing_origins}

        missing_origins = list()
        deleted_origins = set()

        for origin in needed_origins:
            if origin not in origin_map:
                missing_origins.append(origin)
            else:
                if origin_map[origin].is_deleted:
                    deleted_origins.add(origin)

        if missing_origins:
            name_map = {int(p.productCode): p.name for p in payload.raw_products if p.productCode}

            to_insert = list()
            for origin in missing_origins:
                to_insert.append({"origin": origin,
                                  "title": name_map.get(origin),
                                  "link": None,
                                  "pics": None,
                                  "preview": None,
                                  "is_deleted": False})

            await session.execute(insert(ProductOrigin), to_insert)

        default_range = (await session.execute(select(RewardRange)
                                               .where(RewardRange.is_default == True)
                                               .options(selectinload(RewardRange.lines)))).scalar_one()

        reward_lines = [RewardRangeLineSchema.model_validate(line) for line in default_range.lines]

        total_inserted = 0

        for vsl in payload.linked_VSL:
            vsl_id = vsl.id
            products = vsl_products[vsl_id]

            await session.execute(delete(ParsingLine).where(ParsingLine.vsl_id == vsl_id))

            new_rows = list()
            seen_origins = set()

            for p in products:
                if not p.productCode:
                    continue

                origin = int(p.productCode)
                if origin in deleted_origins:
                    continue

                if origin in seen_origins:
                    continue
                seen_origins.add(origin)

                input_price = p.price
                output_price = cost_process(input_price, reward_lines)

                new_rows.append({"vsl_id": vsl_id,
                                 "origin": origin,
                                 "shipment": p.delivery,
                                 "warranty": None,
                                 "input_price": input_price,
                                 "output_price": output_price,
                                 "optional": f"{int(p.amount)} шт",
                                 "profit_range_id": default_range.id})

            if new_rows:
                await session.execute(insert(ParsingLine), new_rows)
                total_inserted += len(new_rows)

            await session.execute(
                update(VendorSearchLine).where(VendorSearchLine.id == vsl_id).values(
                    dt_parsed=datetime.now(timezone.utc)))

        await session.commit()

        return {"status": "ok", "inserted": total_inserted}
