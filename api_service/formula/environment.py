import re

from jinja2 import Environment, StrictUndefined, TemplateSyntaxError
from api_service.formula.filters import register_builtin_filters

env = Environment(
    autoescape=False,
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True
)

register_builtin_filters(env)


def render_formula(formula: str, context: dict) -> str:
    try:
        template = env.from_string(formula)
        return template.render(context)
    except Exception as e:
        raise ValueError(f"Render error: {e}")


def validate_formula(formula: str) -> list[str]:
    errors = list()

    if not formula or not formula.strip():
        errors.append("Формула пуста")
        return errors

    if not re.search(r"{{.*?}}", formula, flags=re.DOTALL):
        errors.append("Формула должна содержать хотя бы один блок {{ ... }}")

    if formula.count("{{") != formula.count("}}"):
        errors.append("Количество {{ и }} не совпадает")

    try:
        env.from_string(formula)
    except TemplateSyntaxError as e:
        errors.append(f"Синтаксическая ошибка Jinja: {e.message}")
    except Exception as e:
        errors.append(f"Ошибка Jinja: {e}")

    allowed_filters = set(env.filters.keys())

    filters_found = re.findall(r"\|\s*(\w+)", formula)
    for f in filters_found:
        if f not in allowed_filters:
            errors.append(f"Неизвестный фильтр: {f}")

    filter_calls = re.findall(r"\|\s*(\w+)\s*\((.*?)\)", formula)

    STRING_PATTERN = r"^(['\"])(.*)\1$"
    NUMBER_PATTERN = r"^\d+(\.\d+)?$"
    IDENT_PATTERN = r"^[A-Za-z_][A-Za-z0-9_\.]*$"

    for filter_name, args in filter_calls:
        if filter_name not in allowed_filters:
            continue

        args_list = [a.strip() for a in args.split(",") if a.strip()]

        for arg in args_list:
            if (
                    re.match(STRING_PATTERN, arg) or
                    re.match(NUMBER_PATTERN, arg) or
                    re.match(IDENT_PATTERN, arg)
            ):
                continue

            errors.append(f"Некорректный аргумент '{arg}' в фильтре {filter_name}")

    return errors
