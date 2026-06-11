from jinja2 import Undefined

from app_utils import MONTHS_TO_CYRILLIC


def filter_contains(items, key, substring):
    if isinstance(items, dict):
        value = items.get(key)
        if isinstance(value, str) and substring in value:
            return items
        return ""

    if isinstance(items, (list, tuple)):
        result = []
        for item in items:
            if isinstance(item, dict):
                value = item.get(key)
                if isinstance(value, str) and substring in value:
                    result.append(item)
        return result if result else ""

    if isinstance(items, str):
        return items if substring in items else ""

    return ""


def filter_not_contains(items, key, substring):
    if isinstance(items, dict):
        value = items.get(key)
        if isinstance(value, str) and substring not in value:
            return items
        return ""

    if isinstance(items, (list, tuple)):
        result = []
        for item in items:
            if isinstance(item, dict):
                value = item.get(key)
                if isinstance(value, str) and substring not in value:
                    result.append(item)
        return result if result else ""

    if isinstance(items, str):
        return items if substring not in items else ""

    return ""


def optional(value, key):
    if isinstance(value, Undefined) or value is None:
        return ""
    if isinstance(value, dict):
        return value.get(key, "")

    return ""


def get_param(info: dict, paths: list):
    if not info or not paths:
        return ""
    for scheme in paths:
        category = scheme.category
        param = scheme.param
        if category not in info:
            continue
        block = info[category]
        if isinstance(block, dict) and param in block:
            value = block[param]
            if value not in (None, "", []):
                return value
    return ""


def _cut_generic(value: str, substring: str, index: int, direction: str):
    if not isinstance(value, str):
        return value

    pos = value.find(substring)
    if pos == -1:
        return value

    left = value[:pos].rstrip()
    right = value[pos + len(substring):].strip()

    left_words = left.split()
    right_words = right.split()

    if direction == "left":
        if index == 0:
            return left
        if len(right_words) < index:
            return value
        extra = " ".join(right_words[:index])
        return f"{left} {substring} {extra}".strip()

    if direction == "right":
        if index == 0:
            return right
        if len(left_words) < index:
            return value
        extra = " ".join(left_words[-index:])
        return f"{extra} {substring} {right}".strip()

    return value


def cut_left(value: str, substring: str, index: int = 0):
    return _cut_generic(value, substring, index, "left")


def cut_right(value: str, substring: str, index: int = 0):
    return _cut_generic(value, substring, index, "right")


def correct_date(value: str):
    if not isinstance(value, str):
        return ""

    parts = value.split(",")
    if len(parts) < 2:
        return value

    year = parts[0].strip()
    month_day = parts[1].strip()
    month_eng = month_day.split(" ")[0]
    month_ru = MONTHS_TO_CYRILLIC.get(month_eng)
    if not month_ru:
        return value

    return f"{month_ru} {year}"


def register_builtin_filters(env):
    env.filters["split"] = lambda s, sep=" ": s.split(sep)
    env.filters["join"] = lambda arr, sep=" ": sep.join(arr)
    env.filters["slice"] = lambda arr, start=0, end=None: arr[start:end]
    env.filters["upper"] = lambda s: s.upper()
    env.filters["lower"] = lambda s: s.lower()
    env.filters["cut_left"] = cut_left
    env.filters["cut_right"] = cut_right
    env.filters["replace"] = lambda s, old, new: s.replace(old, new)
    env.filters["filter_contains"] = filter_contains
    env.filters["filter_not_contains"] = filter_not_contains
    env.filters["optional"] = optional
    env.filters["get_param"] = get_param
    env.filters["correct_date"] = correct_date


FILTER_DOCS = {
    "split": {
        "args": ["separator: string"],
        "description": "Разбивает строку на список по разделителю.",
        "example": '{{ model | split(" ") }}'
    },
    "join": {
        "args": ["separator: string"],
        "description": "Соединяет список строк в одну строку.",
        "example": '{{ ["iPhone", "14", "Plus"] | join(" ") }}'
    },
    "slice": {
        "args": ["start: int", "end?: int"],
        "description": "Возвращает подсписок элементов списка или подстроку строки.",
        "example": '{{ model | split(" ") | slice(1) }}'
    },
    "upper": {
        "args": [],
        "description": "Преобразует строку в верхний регистр.",
        "example": '{{ model | upper }}'
    },
    "lower": {
        "args": [],
        "description": "Преобразует строку в нижний регистр.",
        "example": '{{ model | lower }}'
    },
    "replace": {
        "args": ["old: string", "new: string"],
        "description": "Заменяет подстроку в строке.",
        "example": '{{ model | replace("Apple", "") }}'
    },
    "filter_contains": {
        "args": ["key: string", "substring: string"],
        "description": "Фильтрует список словарей, оставляя элементы, где item[key] содержит substring.",
        "example": '{{ items | filter_contains("value", "eSim") }}'
    },
    "filter_not_contains": {
        "args": ["key: string", "substring: string"],
        "description": "Фильтрует список словарей, исключая элементы, где item[key] содержит substring.",
        "example": '{{ items | filter_not_contains("value", "eSim") }}'
    },
    "attr": {
        "args": ["key: string"],
        "description": "Извлекает поле из словаря.",
        "example": '{{ item | attr("alias") }}'
    },
    "first": {
        "args": [],
        "description": "Возвращает первый элемент списка.",
        "example": '{{ items | first }}'
    },
    "optional": {
        "args": ["key: string"],
        "description": "Безопасно извлекает поле из словаря. Если значение отсутствует — возвращает пустую строку.",
        "example": '{{ attributes.Watch_Display_Size | optional("alias") }}'
    },
    "cut_left": {
        "args": ["substring: string", "index: int"],
        "description": (
            "Универсальный фильтр обрезки строки слева. Ищет подстроку и возвращает левую часть строки, "
            "а также указанное количество слов после подстроки. "
            "index=0 — удалить подстроку и всё, что справа. "
            "index=1 — оставить подстроку и одно слово после неё. "
            "Если подстрока не найдена или index превышает количество слов — возвращает исходную строку."
        ),
        "example": '{{ "6.88 inches diagonal size" | cut_left("inches", 1) }}'
    },

    "cut_right": {
        "args": ["substring: string", "index: int"],
        "description": (
            "Зеркальный фильтр к cut_left. Работает вправо: ищет подстроку и возвращает правую часть строки, "
            "а также указанное количество слов перед подстрокой. "
            "index=0 — удалить подстроку и всё, что слева. "
            "index=1 — оставить одно слово перед подстрокой. "
            "Если подстрока не найдена или index превышает количество слов — возвращает исходную строку."
        ),
        "example": '{{ "6.88 inches diagonal size" | cut_right("inches", 1) }}'
    },
    "correct_date": {
        "args": [],
        "description": "Преобразует дату формата '2025, September 02' в формат 'Сентябрь 2025'. "
                       "Использует встроенный словарь английских месяцев и возвращает только месяц и год. "
                       "Если формат не распознан — возвращает исходную строку.",
        "example": '{{ "2025, September 02" | correct_date }}'
    },
    "get_param": {
        "args": ["info (dict) — JSON-данные товара." "paths (list[SpecsParamScheme]) — список возможных путей."],
        "description": "Универсальный фильтр для извлечения значения параметра из структуры info. "
                       "Работает по списку схем SpecsParamScheme, каждая из которых содержит: "
                       "- category: имя категории в JSON "
                       "- param: имя параметра внутри категории",
        "example": '{{ get_param(info, display_resolution_paths) }}'
    }
}
