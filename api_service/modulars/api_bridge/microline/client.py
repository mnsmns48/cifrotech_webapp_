from aiohttp import ClientSession, ClientResponseError


class MicrolineClient:

    def __init__(self, http: ClientSession):
        self.http = http

    @staticmethod
    async def _auth_headers(vendor):
        return {"Authorization": f"Bearer {vendor.api_token.access_token}",
                "Content-Type": "application/json"}

    async def _request(self, vendor, method: str, path: str, **kwargs):
        url = f"{vendor.source}/api/v1{path}"
        headers = await self._auth_headers(vendor)

        async with self.http.request(method, url, headers=headers, **kwargs) as resp:
            if resp.status >= 400:
                raise ClientResponseError(request_info=resp.request_info,
                                          history=resp.history,
                                          status=resp.status,
                                          message=await resp.text())
            return await resp.json()

    async def get_categories(self, vendor, parent_id=None):
        params = {"parentId": parent_id} if parent_id is not None else None
        return await self._request(vendor, "GET", "/categories", params=params)

    async def get_products(self, vendor, contractor_id, delivery_location_id, category_id, page=1, limit=200):
        params = {"contractorId": contractor_id,
                  "deliveryLocationId": delivery_location_id,
                  "categoryId": category_id,
                  "page": page,
                  "limit": limit}

        return await self._request(vendor, "GET", "/products", params=params)

    async def get_links(self, vendor):
        return await self._request(vendor, "GET", "/links")

    async def get_prices(self, vendor):
        return await self._request(vendor, "GET", "/prices")

    async def get_availability(self, vendor):
        return await self._request(vendor, "GET", "/availability")

    async def sync(self, vendor):
        return await self._request(vendor, "POST", "/sync")

    async def get_me(self, vendor):
        return await self._request(vendor, "GET", "/me")

    async def get_contractors(self, vendor):
        return await self._request(vendor, "GET", "/contractors")
