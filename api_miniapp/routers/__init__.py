from fastapi import APIRouter

from api_miniapp.routers.hub_product import hub_product

miniapp_router = APIRouter(prefix="/miniapp")

miniapp_router.include_router(hub_product)