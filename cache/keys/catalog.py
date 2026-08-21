def catalog_products_key(path: str, filters_hash: str, page: int, limit: int) -> str:
    return f"catalog:v3:category:{path}:{filters_hash}:page={page}:limit={limit}"
