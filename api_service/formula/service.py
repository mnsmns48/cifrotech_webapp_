from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from api_service.formula.environment import validate_formula, render_formula
from models import FormulaExpression


class FormulaService:
    @staticmethod
    async def get_all(session: AsyncSession):
        result = await session.execute(select(FormulaExpression))
        return result.scalars().all()

    @staticmethod
    async def get_by_id(session: AsyncSession, formula_id: int):
        result = await session.execute(
            select(FormulaExpression).where(FormulaExpression.id == formula_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_name(session: AsyncSession, name: str):
        result = await session.execute(
            select(FormulaExpression).where(FormulaExpression.name == name)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_default(session: AsyncSession, entity_type: str | None = None):
        query = select(FormulaExpression).where(FormulaExpression.is_default == True)

        if entity_type:
            query = query.where(FormulaExpression.entity_type == entity_type)

        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(session: AsyncSession, data):

        validate_formula(data.formula)

        if data.is_default:
            await session.execute(
                update(FormulaExpression)
                .where(FormulaExpression.entity_type == data.entity_type)
                .values(is_default=False)
            )

        formula = FormulaExpression(**data.dict())
        session.add(formula)
        await session.commit()
        await session.refresh(formula)
        return formula

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
        return render_formula(formula, context)

    @staticmethod
    async def validate(formula: str):
        try:
            validate_formula(formula)
            return True, None
        except Exception as e:
            return False, str(e)
