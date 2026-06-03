from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.modulars.desc_builder.crud import generate_description_db
from api_service.schemas import FormulaIdObj, FormulaEntityTypeScheme, GenerateDescriptionPayload, \
    FetchComposerResponse, TypeModel, BrandModel, FormulaResponse
from api_service.schemas.desc_builder import SpecsComposerExpandedScheme
from models import DescBuilderFormulaLink, FormulaEntityType, SpecsComposer, FormulaExpression


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

    @staticmethod
    async def fetch_composer(formula_entity_type_id: int, session: AsyncSession):
        stmt_entity = (select(FormulaEntityType).where(FormulaEntityType.id == formula_entity_type_id))
        entity_type = (await session.execute(stmt_entity)).scalar_one_or_none()

        if not entity_type:
            return FetchComposerResponse(entity_type=None, composers=[])

        stmt_composers = (select(SpecsComposer).join(SpecsComposer.formula).options(
            selectinload(SpecsComposer.formula).selectinload(FormulaExpression.entity_type),
            selectinload(SpecsComposer.type),
            selectinload(SpecsComposer.brand),
        )
                          .where(FormulaExpression.entity_type_id == formula_entity_type_id)
                          )

        composers = (await session.execute(stmt_composers)).scalars().all()

        composer_items = []
        for comp in composers:
            composer_items.append(
                SpecsComposerExpandedScheme(id=comp.id, type=TypeModel(id=comp.type.id, type=comp.type.type),
                                            brand=(BrandModel(id=comp.brand.id,
                                                              brand=comp.brand.brand) if comp.brand else None),
                                            source=comp.source,
                                            formula=FormulaResponse.model_validate(comp.formula)))
        return FetchComposerResponse(entity_type_id=formula_entity_type_id,
                                     composers=composer_items)
