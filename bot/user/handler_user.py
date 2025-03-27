import aiohttp
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.api import notify_new_user, get_bot_username
from bot.bot_settings import bot_conf
from bot.core import user_spotted, get_option_value, update_bot
from bot.api import upload_photo_to_telegram
from cfg import BASE_DIR
from engine import pg_engine

tg_user_router = Router()


@tg_user_router.message(CommandStart())
async def start(m: Message) -> None:
    message_data = {'id_': m.from_user.id, 'fullname': m.from_user.full_name, 'username': m.from_user.username}
    async with aiohttp.ClientSession() as client_session, pg_engine.tg_session() as pg_session:
        await notify_new_user(
            session=client_session,
            bot_token=bot_conf.BOT_TOKEN.get_secret_value(),
            chat_id=bot_conf.TELEGRAM_ADMIN_ID[0],
            username=message_data['username'], fullname=message_data['fullname']
        )
        bot_username = await get_bot_username(
            session=client_session,
            bot_token=bot_conf.BOT_TOKEN.get_secret_value()
        )
        await user_spotted(session=pg_session, data=message_data)
        main_pic = await get_option_value(session=pg_session, username=bot_username, field='main_pic')
        if not main_pic:
            pic = await upload_photo_to_telegram(
                session=client_session,
                file_path=f'{BASE_DIR}/bot/main_photo.jpg',
                token=bot_conf.BOT_TOKEN.get_secret_value(),
                chat_id=str(m.chat.id)
            )
            await update_bot(session=pg_session, **{'username': bot_username, 'main_pic': pic})
        else:
            await m.answer_photo(
                photo=main_pic,
                caption=f'Привет, {m.from_user.full_name}, этот БОТ показывает наличие и цены '
                        f'в салоне мобильной связи ЦИФРОТЕХ\n\n'
                        f'Телеграм канал @cifrotechmobile\n\n'
                        f'Управление через кнопки ↓ ↓ ↓ ↓ ↓ ↓ '
            )