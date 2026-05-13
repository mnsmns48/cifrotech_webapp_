from collections import OrderedDict


def normalize_route(route):
    by_id = {lvl.id: lvl for lvl in route}
    root = next(lvl for lvl in route if lvl.parent_id not in by_id)

    ordered = []
    cur = root
    while cur:
        ordered.append(cur)
        cur = next((lvl for lvl in route if lvl.parent_id == cur.id), None)
    return ordered


def filter_unique_origins_by_attrs(models, attrs_map):
    for model in models:
        for origin in model.origins:
            origin.attrs = attrs_map.get(origin.origin, [])
        groups = OrderedDict()
        for origin in model.origins:
            key = frozenset((attr.key.id, attr.value) for attr in (origin.attrs or []))
            groups.setdefault(key, []).append(origin)
        filtered = list()
        for key, origins in groups.items():
            min_price_origin = min(origins, key=lambda o: o.input_price or float("inf"))
            filtered.append(min_price_origin)
        model.origins = sorted(filtered, key=lambda o: o.input_price or float("inf"))
