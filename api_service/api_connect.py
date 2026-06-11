from datetime import datetime, timedelta

import jwt
from aiohttp import ClientSession

from config import settings


def create_service_token() -> str:
    now = datetime.utcnow()
    payload = {"service": settings.api.service_name,
               "iss": settings.api.service_name,
               "sub": f"{settings.api.service_name}->digitaltube",
               "iat": now,
               "exp": now + timedelta(minutes=5)}

    return jwt.encode(payload, settings.api.service_shared_secret, algorithm="HS256")


async def get_one_by_dtube(session: ClientSession, title: str):
    url = f"{settings.api.digitaltube_url}/get_one/"
    async with session.post(url, params={"data": title}, headers={"Accept": "application/json"}) as response:
        if response.status == 200:
            data = await response.json()
            if data:
                return data
    return None


async def get_items_by_params(session: ClientSession, item: str):
    url = f"{settings.api.digitaltube_url}/get_dependency_list/"
    async with session.post(url, params={"item": item}, headers={"Accept": "application/json"}) as response:
        if response.status == 200:
            data = await response.json()
            if data:
                return data
    return None
