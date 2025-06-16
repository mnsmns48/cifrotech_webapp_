import math


def cost_process(n, reward_ranges):
    for line_from, line_to, is_percent, extra in reward_ranges:
        if line_from <= n < line_to:
            if is_percent:
                addition = n * extra / 100
            else:
                addition = extra
            result = n + addition
            return math.ceil(result / 100) * 100
    return n


def cost_value_update(items: list[dict], ranges: list) -> list:
    for item in items:
        if item['origin'] and item['input_price']:
            item['output_price'] = cost_process(item['input_price'], ranges)
    return items



# @parsing_router.put("/update_parsing_item/{origin}")
# async def update_parsing_item(origin: str, data: DetailDependenciesUpdate,
#                               session: AsyncSession = Depends(db.scoped_session_dependency)):
#     stmt = select(DetailDependencies).where(DetailDependencies.origin == origin)
#     result = await session.execute(stmt)
#     item = result.scalars().first()
#     if not item:
#         raise HTTPException(status_code=404, detail="Запись с таким origin не найдена")
#     payload = data.model_dump(exclude_unset=True)
#     if not payload:
#         return "Данные для изменения не переданы"
#     updates = {k: v for k, v in payload.items() if getattr(item, k, None) != v or v is None}
#     if not updates:
#         return "Нет изменений"
#     for k, v in updates.items():
#         setattr(item, k, v)
#     await session.commit()
#     return {"Изменены поля записи": list(updates.keys())}
