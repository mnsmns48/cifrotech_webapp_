from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.modulars.formula.environment import render_formula
from api_service.schemas import GenerateDescriptionPayload
from models import ProductFeaturesGlobal, DescBuilder, FormulaExpression


async def generate_description_db(payload: GenerateDescriptionPayload, session: AsyncSession):
    # 1. Загружаем Info из product_features
    stmt_features = select(ProductFeaturesGlobal).where(
        ProductFeaturesGlobal.id == payload.product_features_id
    )
    result = await session.execute(stmt_features)
    features = result.scalar_one_or_none()

    if not features or not features.info:
        return {"description": ""}

    info = features.info
    # print(info)

    # 2. Загружаем ВСЕ активные блоки DescBuilder (без type_id и brand_id)
    stmt_blocks = (
        select(DescBuilder)
        .where(DescBuilder.is_active.is_(True))
        .order_by(DescBuilder.order_index.asc())
        .options(selectinload(DescBuilder.formula))
    )

    result = await session.execute(stmt_blocks)
    blocks = result.scalars().all()

    if not blocks:
        return {"description": ""}

    # 3. Все блоки используют одну формулу → берём формулу из первого блока
    formula: FormulaExpression = blocks[0].formula
    if not formula:
        return {"description": ""}

    # 4. Выполняем формулу один раз
    raw_output = render_formula(formula.formula, {"info": info})

    if raw_output.startswith("__MISSING_ATTRIBUTES__"):
        return {"description": ""}

    # 5. Разбиваем результат на строки
    lines = [line.strip() for line in raw_output.split("\n") if line.strip()]

    # 6. Сопоставляем строки с блоками DescBuilder
    result_lines = []
    for index, block in enumerate(blocks):
        if index < len(lines):
            result_lines.append(lines[index])

    # 7. Склеиваем строки
    final_description = "\n".join(result_lines)

    return {"description": final_description}

