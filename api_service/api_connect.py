import asyncio
from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt
from aiohttp import ClientSession, ClientConnectorError, ContentTypeError, ClientResponseError, ClientTimeout

from api_service.schemas import UpdateProductFromDTPayload, CreateNewEntityRequest, CreateFeaturesGlobal
from config import settings

BASE_DTUBE_URL = settings.api.digitaltube_url


def create_dtube_token() -> str:
    now = datetime.now(timezone.utc)
    payload = {"service": settings.api.api_service_name,
               "iss": settings.api.api_service_name,
               "sub": f"{settings.api.api_service_name}->digitaltube",
               "iat": now,
               "exp": now + timedelta(minutes=5)}

    return jwt.encode(payload, settings.api.api_service_shared_secret, algorithm="HS256")


async def get_one_by_dtube(session: ClientSession, title: str):
    url = f"{BASE_DTUBE_URL}/get_one/"
    token = create_dtube_token()
    async with session.post(url, params={"data": title}, headers={"Accept": "application/json",
                                                                  "Authorization": f"Bearer {token}"}) as response:
        if response.status == 200:
            data = await response.json()
            if data:
                return data
    return None


async def get_items_by_params(session: ClientSession, item: str):
    url = f"{BASE_DTUBE_URL}/get_dependency_list/"
    token = create_dtube_token()
    async with session.post(url, params={"item": item}, headers={"Accept": "application/json",
                                                                 "Authorization": f"Bearer {token}"}) as response:
        if response.status == 200:
            data = await response.json()
            if data:
                return data
    return None


async def update_product_from_dtube(payload: UpdateProductFromDTPayload, session: ClientSession):
    url = f"{BASE_DTUBE_URL}/refresh_item"
    token = create_dtube_token()
    async with session.post(url,
                            json={"title": payload.title, "type": payload.type, "brand": payload.brand},
                            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"}) as response:
        if response.status != 200:
            return None
        return await response.json()


async def can_connect(session: ClientSession) -> bool:
    url = f"{BASE_DTUBE_URL}/welcome"
    try:
        timeout = ClientTimeout(total=5)
        async with session.get(url, timeout=timeout) as response:
            if response.status != 200:
                return False

            data = await response.json()
            return data.get("status") == "ok"

    except (ClientConnectorError, asyncio.TimeoutError, ClientResponseError, ContentTypeError, Exception):
        return False


async def create_new_entity_in_server(payload: CreateNewEntityRequest, session: ClientSession):
    url = f"{BASE_DTUBE_URL}/create_new_entity/"
    token = create_dtube_token()
    async with session.post(url,
                            json=payload.model_dump(),
                            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"}) as response:
        if response.status != 200:
            return None
        return await response.json()


async def create_new_product_in_server(payload: CreateFeaturesGlobal, session: ClientSession):
    url = f"{BASE_DTUBE_URL}/create_new_feature_global/"
    token = create_dtube_token()
    async with session.post(url,
                            json={"title": payload.title,
                                  "type_obj": payload.type_obj.type,
                                  "brand_obj": payload.brand_obj.brand},
                            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"}) as response:
        if response.status != 200:
            return None
        return await response.json()


async def create_pros_cons_value_in_server(product_title: str,
                                           attribute: Literal["advantage", "disadvantage"],
                                           value: str,
                                           session: ClientSession):
    url = f"{BASE_DTUBE_URL}/add_pros_cons_value/"
    token = create_dtube_token()
    async with session.post(url,
                            json={"product_title": product_title, "attribute": attribute, "value": value},
                            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"}) as response:
        if response.status != 200:
            return None
        return await response.json()


async def update_pros_cons_value_in_server(product_title: str,
                                           attribute: Literal["advantage", "disadvantage"],
                                           value: str,
                                           new_value: str,
                                           session: ClientSession):
    url = f"{BASE_DTUBE_URL}/update_pros_cons_value/"
    token = create_dtube_token()
    async with session.post(url,
                            json={"product_title": product_title, "attribute": attribute, "value": value,
                                  "new_value": new_value},
                            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"}) as response:
        if response.status != 200:
            return None
        return await response.json()


async def delete_pros_cons_value_in_server(product_title: str,
                                           attribute: Literal["advantage", "disadvantage"],
                                           value: str,
                                           session: ClientSession):
    url = f"{BASE_DTUBE_URL}/delete_pros_cons_value/"
    token = create_dtube_token()
    async with session.post(url,
                            json={"product_title": product_title, "attribute": attribute, "value": value},
                            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"}) as response:
        if response.status != 200:
            return None
        return await response.json()


async def insert_bulk_data_in_server(feature_title: str, bulk: list, session: ClientSession):
    url = f"{BASE_DTUBE_URL}/insert_bulk_data_in_info/"
    token = create_dtube_token()
    async with session.post(url,
                            json={"feature_title": feature_title, "bulk": bulk},
                            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"}) as response:
        if response.status != 200:
            return None
        return await response.json()


async def create_new_info_category_in_server(feature_title: str, category: str, session: ClientSession):
    url = f"{BASE_DTUBE_URL}/create_new_info_category/"
    token = create_dtube_token()
    async with session.post(url,
                            json={"feature_title": feature_title, "category": category},
                            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"}) as response:
        if response.status != 200:
            return None
        return await response.json()


async def delete_info_category_in_server(feature_title: str, category: str, session: ClientSession):
    url = f"{BASE_DTUBE_URL}/delete_info_category/"
    token = create_dtube_token()
    async with session.post(url,
                            json={"feature_title": feature_title, "category": category},
                            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"}) as response:
        if response.status != 200:
            return None
        return await response.json()


async def update_info_category_in_server(feature_title: str, category: str, new_category: str, session: ClientSession):
    url = f"{BASE_DTUBE_URL}/update_info_category/"
    token = create_dtube_token()
    async with session.post(url,
                            json={"feature_title": feature_title, "category": category, "new_category": new_category},
                            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"}) as response:
        if response.status != 200:
            return None
        return await response.json()


async def create_features_inner_row_in_server(feature_title: str,
                                              category_title: str,
                                              new_param: str,
                                              new_value: str,
                                              session: ClientSession):
    url = f"{BASE_DTUBE_URL}/add_new_features_inner_row/"
    token = create_dtube_token()
    async with session.post(url,
                            json={"feature_title": feature_title,
                                  "category_title": category_title,
                                  "new_param": new_param,
                                  "new_value": new_value},
                            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"}) as response:
        if response.status != 200:
            return None
        return await response.json()


async def update_features_inner_row_in_server(feature_title: str,
                                              category_title: str,
                                              new_param: str,
                                              new_value: str,
                                              old_param: str,
                                              old_value: str,
                                              session: ClientSession):
    url = f"{BASE_DTUBE_URL}/update_features_inner_row/"
    token = create_dtube_token()
    async with session.post(url,
                            json={"feature_title": feature_title,
                                  "category_title": category_title,
                                  "new_param": new_param,
                                  "new_value": new_value,
                                  "old_param": old_param,
                                  "old_value": old_value},
                            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"}) as response:
        if response.status != 200:
            return None
        return await response.json()


async def delete_features_inner_row_in_server(feature_title: str,
                                              category_title: str,
                                              new_param: str,
                                              new_value: str,
                                              session: ClientSession):
    url = f"{BASE_DTUBE_URL}/delete_features_inner_row/"
    token = create_dtube_token()
    async with session.post(url,
                            json={"feature_title": feature_title,
                                  "category_title": category_title,
                                  "new_param": new_param,
                                  "new_value": new_value},
                            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"}) as response:
        if response.status != 200:
            return None
        return await response.json()
