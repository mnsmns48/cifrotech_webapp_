from typing import List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.modulars.desc_builder.crud import generate_description_db
from api_service.schemas import FormulaIdObj, FormulaEntityTypeScheme, GenerateDescriptionPayload, \
    FetchComposerResponse, TypeModel, FormulaResponse
from api_service.schemas.desc_builder import SpecsComposerExpandedScheme, SpecsPathRequest, SpecPathResponse, \
    CreateSpecsComposer, SaveSpecsComposer, SpecsComposerResponse
from models import DescBuilderFormulaLink, SpecsComposer, FormulaExpression, SpecPath, ProductType, \
    ProductFeaturesGlobal


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
    async def generate_description(payload: GenerateDescriptionPayload, session: AsyncSession) -> FetchComposerResponse:
        return await generate_description_db(payload, session)

    @staticmethod
    async def fetch_composer(formula_entity_type_id: int, session: AsyncSession):
        stmt_composers = (select(SpecsComposer).join(SpecsComposer.formula)
                          .options(
            selectinload(SpecsComposer.formula).selectinload(FormulaExpression.entity_type),
            selectinload(SpecsComposer.type),
        ).where(FormulaExpression.entity_type_id == formula_entity_type_id))
        composers = (await session.execute(stmt_composers)).scalars().all()
        composer_items = list()
        for comp in composers:
            composer_items.append(
                SpecsComposerExpandedScheme(id=comp.id, type=TypeModel(id=comp.type.id, type=comp.type.type),
                                            source=comp.source,
                                            formula=FormulaResponse.model_validate(comp.formula)))
        return FetchComposerResponse(entity_type_id=formula_entity_type_id,
                                     composers=composer_items)

    @staticmethod
    async def fetch_spec_path(payload: SpecsPathRequest, session: AsyncSession) -> List[SpecPathResponse]:
        stmt = (select(SpecPath).where(and_(SpecPath.formula_id == payload.formula_id),
                                       (SpecPath.source == payload.source)))
        rows = (await session.execute(stmt)).scalars().all()
        return [SpecPathResponse(title=row.title, path=row.path, icon=row.icon) for row in rows]

    @staticmethod
    async def create_new_composer(formula_entity_type_id: int, session) -> CreateSpecsComposer:
        types_query = await session.execute(select(ProductType))
        types = types_query.scalars().all()
        sources_query = await session.execute(
            select(ProductFeaturesGlobal.source)
            .where(ProductFeaturesGlobal.source.isnot(None))
            .distinct())
        sources = [row[0] for row in sources_query.all()]
        formulas_query = await session.execute(
            select(FormulaExpression)
            .options(selectinload(FormulaExpression.entity_type))
            .where(FormulaExpression.entity_type_id == formula_entity_type_id)
            .order_by(FormulaExpression.name)
        )
        formulas = formulas_query.scalars().all()
        return CreateSpecsComposer(types=types, sources=sources, formulas=formulas)

    @staticmethod
    async def save_new_composer(payload: SaveSpecsComposer, session: AsyncSession) -> SpecsComposerResponse:
        new_obj = SpecsComposer(type_id=payload.type_id, source=payload.source, formula_id=payload.formula_id)
        session.add(new_obj)
        await session.commit()
        await session.refresh(new_obj)
        return SpecsComposerResponse.model_validate(new_obj)
