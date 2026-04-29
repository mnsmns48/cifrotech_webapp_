from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.analytics.schemas import ProductTypeWeightRuleSchema
from api_service.modulars.analytics.service import AnalyticService
from engine import db

analytics_router = APIRouter(tags=['Analytics'], prefix='/analytics')


@analytics_router.get("/", response_model=list[ProductTypeWeightRuleSchema])
async def get_analytic_table(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await AnalyticService.fetch_all(session)
