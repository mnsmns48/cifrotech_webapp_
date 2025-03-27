import aiohttp
from aiohttp import ClientSession

api_url = 'https://api.telegram.org/bot'


async def notify_new_user(session: ClientSession, bot_token: str, chat_id: str, username: str,
                          fullname: str):
    message_text = f"New User {fullname} {username}"
    await session.get(url=f"{api_url}bot{bot_token}/sendMessage",
                      params={"chat_id": chat_id, "text": message_text})


async def get_bot_username(session: ClientSession, bot_token: str) -> str:
    url = f"{api_url}{bot_token}/getMe"
    async with session.get(url) as response:
        if response.status == 200:
            bot_data = await response.json()
            return bot_data.get('result', {}).get('username')
        else:
            raise Exception(f"Ошибка запроса: {response.status}")


async def upload_photo_to_telegram(session: ClientSession,
                                   file_path: str,
                                   token: str,
                                   chat_id: str) -> str:
    url = api_url + token + '/sendPhoto'
    with open(file_path, 'rb') as photo:
        form_data = aiohttp.FormData()
        form_data.add_field('chat_id', chat_id)
        form_data.add_field('photo', photo)
        async with session.post(url, data=form_data) as response:
            if response.status == 200:
                data = await response.json()
                return data['result']['photo'][-1]['file_id']
            else:
                raise Exception(f"Ошибка при загрузке фотографии: {response.status}")
