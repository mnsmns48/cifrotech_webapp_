import emoji
from bs4 import BeautifulSoup


def sanitize_emoji(text):
    return emoji.replace_emoji(text, replace='')


def responses(response: str, is_ok: bool, message: str = '') -> dict:
    return {'response': response,
            'is_ok': is_ok,
            'msg': message,
            'soup': BeautifulSoup(markup=response, features='lxml')}
