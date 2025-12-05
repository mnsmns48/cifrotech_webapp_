from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

webapp_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Открыть",
                web_app=WebAppInfo(url="https://24cifrotech.ru/webapp")
            )
        ]
    ]
)