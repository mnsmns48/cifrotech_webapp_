from api_v3.schemas import HubProductSchemeExtV3, SortResponse, CategoryItem, SortOption


def apply_sort(products: list[HubProductSchemeExtV3], items: list[CategoryItem], sort_key: str) -> SortResponse:
    if sort_key == "price_asc":
        products.sort(key=lambda p: (p.output_price or float("inf")))

    elif sort_key == "price_desc":
        products.sort(key=lambda p: -(p.output_price or 0))

    elif sort_key == "updated_desc":
        products.sort(
            key=lambda p: next(i.updated_at for i in items if i.hubstock_id == p.id),
            reverse=True
        )

    elif sort_key == "title_asc":
        products.sort(key=lambda p: p.title.lower() if p.title else "")

    elif sort_key == "title_desc":
        products.sort(key=lambda p: p.title.lower() if p.title else "", reverse=True)

    return SortResponse(
        active=sort_key,
        options=[
            SortOption(key="price_asc", label="Сначала дешевле"),
            SortOption(key="price_desc", label="Сначала дороже"),
            SortOption(key="updated_desc", label="Последние обновлённые"),
            SortOption(key="title_asc", label="от А до Я"),
            SortOption(key="title_desc", label="от Я до А"),
        ],
    )
