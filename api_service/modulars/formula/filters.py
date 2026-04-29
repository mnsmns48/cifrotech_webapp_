from jinja2 import Undefined


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


def register_builtin_filters(env):
    env.filters["split"] = lambda s, sep=" ": s.split(sep)
    env.filters["join"] = lambda arr, sep=" ": sep.join(arr)
    env.filters["slice"] = lambda arr, start=0, end=None: arr[start:end]
    env.filters["upper"] = lambda s: s.upper()
    env.filters["lower"] = lambda s: s.lower()
    env.filters["replace"] = lambda s, old, new: s.replace(old, new)
    env.filters["filter_contains"] = filter_contains
    env.filters["filter_not_contains"] = filter_not_contains
    env.filters["optional"] = optional


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
    }

}
