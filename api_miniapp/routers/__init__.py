from fastapi import APIRouter

from api_miniapp.routers.hub_product import hub_product
from api_miniapp.routers.service import service_mini_app

miniapp_router = APIRouter(prefix="/miniapp")

miniapp_router.include_router(hub_product)
miniapp_router.include_router(service_mini_app)
