import hashlib
import re
from datetime import datetime
from typing import Any, Optional, List, Set

from bs4 import BeautifulSoup

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

MONTHS_TO_CYRILLIC = {"January": "Январь", "February": "Февраль", "March": "Март", "April": "Апрель",
                      "May": "Май", "June": "Июнь", "July": "Июль", "August": "Август",
                      "September": "Сентябрь", "October": "Октябрь", "November": "Ноябрь", "December": "Декабрь"}

TRANSLIT_MAP = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
                "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i",
                "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
                "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
                "у": "u", "ф": "f", "х": "h", "ц": "ts", "ч": "ch",
                "ш": "sh", "щ": "sch", "ы": "y", "э": "e", "ю": "yu",
                "я": "ya"}


def responses(response: str, is_ok: bool, message: str = '') -> dict:
    return {'response': response,
            'is_ok': is_ok,
            'msg': message,
            'soup': BeautifulSoup(markup=response, features='lxml')}


def format_datetime_ru(dt: datetime) -> str:
    return f"{dt.day} {MONTHS_RU[dt.month]} в {dt.strftime('%H:%M')}"


def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        return int(value)
    except ValueError:
        return default


def normalize_pages_list(raw_pages: List[Any]) -> List[int]:
    nums: Set[int] = set()
    for p in (raw_pages or []):
        if isinstance(p, int):
            nums.add(p)
            continue
        try:
            text = getattr(p, "get_text", lambda: str(p))()
            m = re.search(r"(\d+)", str(text).strip())
            if m:
                nums.add(int(m.group(1)))
        except (AttributeError, TypeError, ValueError):
            continue
    return sorted(nums)


def compute_html_hash(html: str) -> str:
    return hashlib.md5(html.encode()).hexdigest()


def count_message(count: int) -> str:
    return f"data: COUNT={count + 20}"


def slugify(text: str) -> str:
    text = text.strip().lower()

    result = []
    for ch in text:
        if ch in TRANSLIT_MAP:
            result.append(TRANSLIT_MAP[ch])
        elif re.match(r"[a-z0-9]", ch):
            result.append(ch)
        else:
            result.append("-")

    slug = "".join(result)
    slug = re.sub(r"[^a-z0-9\-]+", "", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")

    return slug
