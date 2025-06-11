from aiohttp import ClientSession

from config import settings


def deep_decode(obj):
    if isinstance(obj, dict):
        return {deep_decode(key): deep_decode(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [deep_decode(item) for item in obj]
    elif isinstance(obj, str):
        return obj.encode().decode("unicode_escape")
    return obj


async def get_one_by_dtube(session: ClientSession, title: str):
    urls = [
        f"{settings.api.digitaltube_url}/get_one/?data={title}",
        f"{settings.api.digitaltube_url}/get_itemlist/?item={title}"
    ]
    for url in urls:
        async with session.post(url) as response:
            if response.status == 200:
                data = await response.json()
                if data:
                    decoded_data = deep_decode(data)
                    return decoded_data
    return None
