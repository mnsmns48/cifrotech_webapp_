import aiohttp
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from bot.api import notify_new_user, get_bot_username
from bot.crud_bot import user_spotted, get_option_value, update_bot
from bot.api import upload_photo_to_telegram
from bot.user.keyboard import webapp_kb
from bot.user.state import UserMainMenu
from bot.user.dialog import main_hubstock_dialog
from config import BASE_DIR, settings
from engine import db

tg_user_router = Router()

tg_user_router.include_routers(main_hubstock_dialog)


@tg_user_router.message(CommandStart())
async def start(m: Message, dialog_manager: DialogManager) -> None:
    # hello_text = (f'Привет, {m.from_user.full_name}\n\n'
    #               f'Спросить / узнать / выяснить, как заказать можно [тут](https://t.me/cifrotech_mobile)')
    message_data = {'id_': m.from_user.id, 'fullname': m.from_user.full_name, 'username': m.from_user.username}

    async with aiohttp.ClientSession() as client_session, db.tg_session() as pg_session:
        await notify_new_user(
            session=client_session,
            bot_token=settings.bot.bot_token.get_secret_value(),
            chat_id=settings.bot.telegram_admin_id[0],
            username=message_data['username'], fullname=message_data['fullname']
        )
        bot_username = await get_bot_username(
            session=client_session,
            bot_token=settings.bot.bot_token.get_secret_value()
        )
        await user_spotted(session=pg_session, data=message_data)
        # main_pic = await get_option_value(session=pg_session, username=bot_username, field='main_pic')
        # if not main_pic:
        #     pic = await upload_photo_to_telegram(
        #         session=client_session,
        #         file_path=f'{BASE_DIR}/bot/main_photo.jpg',
        #         token=settings.bot.bot_token.get_secret_value(),
        #         chat_id=str(m.chat.id)
        #     )
        #     await m.answer(text=hello_text, parse_mode="MarkdownV2", disable_web_page_preview=True, reply_markup=webapp_kb)
        #     await update_bot(session=pg_session, **{'username': bot_username, 'main_pic': pic})
        # else:
        #     await m.answer_photo(photo=main_pic, caption=hello_text, parse_mode="MarkdownV2",
        #                          disable_web_page_preview=True, reply_markup=webapp_kb)
    await m.answer('Теперь всё в приложении', reply_markup=webapp_kb)
    # await dialog_manager.start(UserMainMenu.start, mode=StartMode.RESET_STACK)
