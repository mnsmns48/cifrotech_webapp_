from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

main_menu_ = [
    [KeyboardButton(text='Актуально в Цифрохаб')],
    [KeyboardButton(text='Наличие в Цифротех', web_app=WebAppInfo(url='https://24cifrotech.ru'))],
]

user_kb = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True, keyboard=main_menu_)
