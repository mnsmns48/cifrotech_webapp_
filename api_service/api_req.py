from aiohttp import ClientSession

from config import settings


def deep_decode(obj):
    if isinstance(obj, dict):
        return {deep_decode(k): deep_decode(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [deep_decode(v) for v in obj]
    if isinstance(obj, str):
        try:
            return obj.encode().decode("unicode_escape")
        except UnicodeDecodeError:
            return obj
    return obj


async def get_one_by_dtube(session: ClientSession, title: str):
    urls = [(f"{settings.api.digitaltube_url}/get_one/", {"data": title}),
            (f"{settings.api.digitaltube_url}/get_itemlist/", {"item": title})]
    for url, payload in urls:
        async with session.post(url, params=payload, headers={"Accept": "application/json"}) as response:
            if response.status == 200:
                data = await response.json()
                if data:
                    decoded_data = deep_decode(data)
                    return decoded_data
    return None


async def get_items_by_brand(session: ClientSession, title: str):
    url = f"{settings.api.digitaltube_url}/get_one/"
    async with session.post(url, params={"data": title}, headers={"Accept": "application/json"}) as response:
        if response.status == 200:
            data = await response.json()
            return data
