from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.api_bridge.microline.client import MicrolineClient
from api_service.modulars.api_bridge.microline.scheme import AddVendorApiSearch, VendorApiSearchResponse, \
    DeleteVendorApiSearch, VendorApiSearchDeleteResponse
from api_service.modulars.api_bridge.token_services import AuthResult
from models import Vendor, VendorApiSearch


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
