from datetime import datetime, timedelta, timezone

import jwt
from aiohttp import ClientSession

from api_service.schemas import UpdateProductFromDTPayload
from config import settings


def create_dtube_token() -> str:
    now = datetime.now(timezone.utc)
    payload = {"service": settings.api.api_service_name,
               "iss": settings.api.api_service_name,
               "sub": f"{settings.api.api_service_name}->digitaltube",
               "iat": now,
               "exp": now + timedelta(minutes=5)}

    return jwt.encode(payload, settings.api.api_service_shared_secret, algorithm="HS256")


async def get_one_by_dtube(session: ClientSession, title: str):
    url = f"{settings.api.digitaltube_url}/get_one/"
    token = create_dtube_token()
    async with session.post(url, params={"data": title}, headers={"Accept": "application/json",
                                                                  "Authorization": f"Bearer {token}"}) as response:
        if response.status == 200:
            data = await response.json()
            if data:
                return data
    return None


async def get_items_by_params(session: ClientSession, item: str):
    url = f"{settings.api.digitaltube_url}/get_dependency_list/"
    token = create_dtube_token()
    async with session.post(url, params={"item": item}, headers={"Accept": "application/json",
                                                                 "Authorization": f"Bearer {token}"}) as response:
        if response.status == 200:
            data = await response.json()
            if data:
                return data
    return None


async def update_product_from_dtube(payload: UpdateProductFromDTPayload, session: ClientSession):
    url = f"{settings.api.digitaltube_url}/refresh_item"
    token = create_dtube_token()
    async with session.post(url,
                            json={"title": payload.title, "type": payload.type, "brand": payload.brand},
                            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"}) as response:
        if response.status != 200:
            return None
        return await response.json()
