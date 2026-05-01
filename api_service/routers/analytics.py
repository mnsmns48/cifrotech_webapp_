from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.analytics.service import AnalyticService
from api_service.schemas import ProductTypeWeightRuleSchema, ProductTypeWeightRuleCreate, ProductTypeWeightRuleDelete, \
    ProductTypeWeightRuleUpdate, ProductTypeWeightRuleSwitch
from engine import db

analytics_router = APIRouter(tags=['Analytics'], prefix='/analytics')


@analytics_router.get("/", response_model=list[ProductTypeWeightRuleSchema])
async def get_analytic_table(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await AnalyticService.fetch_all(session)


@analytics_router.post("/add_rule_line", response_model=ProductTypeWeightRuleSchema)
async def get_analytic_table(payload: ProductTypeWeightRuleCreate,
                             session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await AnalyticService.add_rule_line(payload, session)


@analytics_router.post("/delete_rule_line")
async def delete_rule_line(payload: ProductTypeWeightRuleDelete,
                           session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await AnalyticService.delete_rule_line(rule_id=payload.id, session=session)


@analytics_router.post("/update_rule_line", response_model=ProductTypeWeightRuleSchema)
async def update_rule_line(payload: ProductTypeWeightRuleUpdate,
                           session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await AnalyticService.update_rule_line(payload, session)


@analytics_router.post("/toggle_switch", response_model=ProductTypeWeightRuleSchema)
async def toggle_enabled(payload: ProductTypeWeightRuleSwitch,
                         session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await AnalyticService.toggle_rule_switch(rule_id=payload.id, is_enabled=payload.is_enabled, session=session)
