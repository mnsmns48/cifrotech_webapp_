def normalize_route(route):
    by_id = {lvl.id: lvl for lvl in route}
    root = next(lvl for lvl in route if lvl.parent_id not in by_id)

    ordered = []
    cur = root
    while cur:
        ordered.append(cur)
        cur = next((lvl for lvl in route if lvl.parent_id == cur.id), None)
    return ordered
