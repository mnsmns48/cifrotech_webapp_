from datetime import datetime

import emoji
from bs4 import BeautifulSoup

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}


def sanitize_emoji(text):
    return emoji.replace_emoji(text, replace='')


def responses(response: str, is_ok: bool, message: str = '') -> dict:
    return {'response': response,
            'is_ok': is_ok,
            'msg': message,
            'soup': BeautifulSoup(markup=response, features='lxml')}


def format_datetime_ru(dt: datetime) -> str:
    return f"{dt.day} {MONTHS_RU[dt.month]} в {dt.strftime('%H:%M')}"
