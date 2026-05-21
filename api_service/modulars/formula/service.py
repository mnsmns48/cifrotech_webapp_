from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from api_service.modulars.formula.environment import validate_formula, render_formula
from api_service.schemas import FormulaEntityTypeScheme, CreateFormulaEntityType
from models import FormulaExpression
from models.formula import FormulaEntityType


class FormulaService:
    @staticmethod
    async def get_all(session: AsyncSession):
        result = await session.execute(
            select(FormulaExpression).options(
                selectinload(FormulaExpression.entity_type)
            )
        )
        return result.scalars().all()

    @staticmethod
    async def get_by_id(session: AsyncSession, formula_id: int):
        result = await session.execute(
            select(FormulaExpression).where(FormulaExpression.id == formula_id)
            .options(
                selectinload(FormulaExpression.entity_type)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_name(session: AsyncSession, name: str):
        result = await session.execute(
            select(FormulaExpression).where(FormulaExpression.name == name)
            .options(
                selectinload(FormulaExpression.entity_type)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_default(session: AsyncSession, entity_type: str | None = None):
        query = (select(FormulaExpression).where(FormulaExpression.is_default == True)
        .options(
            selectinload(FormulaExpression.entity_type)
        ))

        if entity_type:
            query = query.where(FormulaExpression.entity_type == entity_type)

        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(session: AsyncSession, data):
        payload = data.dict(exclude_unset=True)
        if "entity_type" in payload:
            payload["entity_type_id"] = payload.pop("entity_type")
        if payload.get("formula"):
            validate_formula(payload["formula"])
        formula = FormulaExpression(**payload)
        session.add(formula)
        await session.commit()
        await session.refresh(formula)
        result = await session.execute(
            select(FormulaExpression)
            .where(FormulaExpression.id == formula.id)
            .options(selectinload(FormulaExpression.entity_type))
        )
        return result.scalar_one()

    @staticmethod
    async def update(session: AsyncSession, formula_id: int, data):
        formula = await FormulaService.get_by_id(session, formula_id)
        if not formula:
            return None

        if data.formula:
            validate_formula(data.formula)

        if data.is_default:
            await session.execute(
                update(FormulaExpression)
                .where(FormulaExpression.entity_type == formula.entity_type)
                .values(is_default=False)
            )

        for key, value in data.dict(exclude_unset=True).items():
            if key == "entity_type":
                formula.entity_type_id = value
            else:
                setattr(formula, key, value)

        await session.commit()
        await session.refresh(formula)
        return formula

    @staticmethod
    async def deactivate(session: AsyncSession, formula_id: int):
        formula = await FormulaService.get_by_id(session, formula_id)
        if not formula:
            return None

        formula.is_active = False
        await session.commit()
        return formula

    @staticmethod
    async def preview(formula: str, context: dict):
        validate_formula(formula)
        return render_formula(formula, context).replace("  ", " ")

    @staticmethod
    async def validate(formula: str):
        try:
            validate_formula(formula)
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    async def set_default(session: AsyncSession, formula_id: int):
        stmt = (update(FormulaExpression).values(is_default=(FormulaExpression.id == formula_id)))
        await session.execute(stmt)
        await session.commit()


class FormulaEntityTypeService:
    @staticmethod
    async def get_formula_entity_types(session: AsyncSession):
        stmt = select(FormulaEntityType)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [FormulaEntityTypeScheme.model_validate(row) for row in rows]

    @staticmethod
    async def create_formula_entity_type(session: AsyncSession,
                                         payload: CreateFormulaEntityType) -> FormulaEntityTypeScheme:
        obj = FormulaEntityType(title_type=payload.title_type, description=payload.description)
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return FormulaEntityTypeScheme.model_validate(obj)

    @staticmethod
    async def update_formula_entity_type(session: AsyncSession, payload) -> FormulaEntityTypeScheme | None:
        stmt = select(FormulaEntityType).where(FormulaEntityType.id == payload.id)
        result = await session.execute(stmt)
        obj = result.scalar_one_or_none()
        if obj is None:
            return None
        obj.title_type = payload.title_type
        obj.description = payload.description
        await session.commit()
        await session.refresh(obj)
        return FormulaEntityTypeScheme.model_validate(obj)

    @staticmethod
    async def delete_formula_entity_type(session: AsyncSession, id_: int) -> bool:
        stmt = select(FormulaEntityType).where(FormulaEntityType.id == id_)
        result = await session.execute(stmt)
        obj = result.scalar_one_or_none()
        if obj is None:
            return False
        await session.delete(obj)
        await session.commit()
        return True
