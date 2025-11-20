import hashlib
import re
from datetime import datetime
from typing import Any, Optional, List, Set

from bs4 import BeautifulSoup

from config import settings

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}


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


def get_url_from_s3(filename: str, path: str) -> str:
    s3 = settings.s3
    base_url = s3.s3_url.removeprefix("https://").rstrip("/")
    return f"https://{s3.bucket_name}.{base_url}/{s3.s3_hub_prefix}/{path}/{filename}"
