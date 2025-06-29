from aiohttp import ClientSession

from config import settings

url = settings.digitaltube


async def get_one_item(session: ClientSession, query_string: str):
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    data = {"title": query_string, "brand": "string", "product_type": "string", "source": "string"}
    async with session.post(url + '/get_one/', json=data, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            return data
