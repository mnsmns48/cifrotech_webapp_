import re

TRANSLIT_MAP = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
                "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i",
                "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
                "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
                "у": "u", "ф": "f", "х": "h", "ц": "ts", "ч": "ch",
                "ш": "sh", "щ": "sch", "ы": "y", "э": "e", "ю": "yu",
                "я": "ya"}


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
