from aiohttp import ClientSession

from cfg import settings

url = settings.digitaltube

async def get_one_item(session: ClientSession, query_string: str):
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    data = {"title": query_string, "brand": "string","product_type": "string","source": "string"}
    async with session.post(url + '/get_one/', json=data, headers=headers) as response:
        print(query_string, response.status)
        if response.status == 200:
            data = await response.json()
            return data
