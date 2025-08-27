from aiohttp import ClientSession

from config import settings


async def get_one_by_dtube(session: ClientSession, title: str):
    url = f"{settings.api.digitaltube_url}/get_one/"
    async with session.post(url, params={"data": title}, headers={"Accept": "application/json"}) as response:
        if response.status == 200:
            data = await response.json()
            if data:
                return data
    return None


async def get_items_by_brand(session: ClientSession, title: str):
    url = f"{settings.api.digitaltube_url}/get_items_by_brand/"
    async with session.post(url, params={"item": title}, headers={"Accept": "application/json"}) as response:
        if response.status == 200:
            data = await response.json()
            if data:
                return data
    return None
