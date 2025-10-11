from aiogram.types import KeyboardButton, WebAppInfo, ReplyKeyboardMarkup

from config import settings

admin_basic_ = [
    [KeyboardButton(text='Продажи сегодня')],
    [KeyboardButton(text='W-APP', web_app=WebAppInfo(url='https://24cifrotech.ru'))],
    [KeyboardButton(text='TEST', web_app=WebAppInfo(url=f"https://24cifrotech.ru/webapp"))],
]

admin_basic_kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=admin_basic_)
