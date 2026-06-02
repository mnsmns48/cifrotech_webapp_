from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.desc_builder.crud import generate_description_db
from api_service.schemas import FormulaIdObj, FormulaEntityTypeScheme, GenerateDescriptionPayload
from models import DescBuilderFormulaLink


class DescBuilder:
    @staticmethod
    async def fetch_formula_link(session):
        stmt = select(DescBuilderFormulaLink).limit(1)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return {"exists": False, "entity_type": None}
        await session.refresh(row, ["entity_type"])
        return {"exists": True, "entity_type": FormulaEntityTypeScheme.model_validate(row.entity_type)}

    @staticmethod
    async def update_formula_link(formula: FormulaIdObj, session: AsyncSession):
        stmt = select(DescBuilderFormulaLink).limit(1)
        result = await session.execute(stmt)
        link = result.scalar_one_or_none()

        if link is None:
            new_link = DescBuilderFormulaLink(entity_type_id=formula.id)
            session.add(new_link)
            await session.commit()
            await session.refresh(new_link)
            return new_link

        link.entity_type_id = formula.id
        await session.commit()
        await session.refresh(link)
        return link

    @staticmethod
    async def generate_description(payload: GenerateDescriptionPayload, session: AsyncSession):
        return await generate_description_db(payload, session)

    # @staticmethod
    # async def fetch_formulas_with_description(formula_id: int, session: AsyncSession):
