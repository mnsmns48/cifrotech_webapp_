from aiogram.types import KeyboardButton, WebAppInfo, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

admin_basic_ = [
    [KeyboardButton(text='Продажи сегодня')],
    [KeyboardButton(text='W-APP', web_app=WebAppInfo(url='https://24cifrotech.ru'))],
]

admin_basic_kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=admin_basic_)
admin_basic_choice_kb = InlineKeyboardBuilder()
admin_basic_choice_kb.add(InlineKeyboardButton(text="обработать предложение [репост]", callback_data="process_vendor_message"))
