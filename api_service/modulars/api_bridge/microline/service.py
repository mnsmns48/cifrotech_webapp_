from fastapi import HTTPException
from api_service.modulars.api_bridge.microline.client import MicrolineClient
from api_service.modulars.api_bridge.token_services import AuthResult
from models import Vendor


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
