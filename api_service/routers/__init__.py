from fastapi import APIRouter, Depends

from api_service.routers.comparison import comparison_router
from api_service.routers.hub import hub_router
from api_service.routers.hubstock import hubstock_router
from api_service.routers.printer import printer_router
from api_service.routers.reward_range import reward_range_router
from api_service.routers.vendor import vendor_router
from api_service.routers.vendor_search_line import vendor_search_line_router
from api_users.dependencies.fastapi_users_dep import current_super_user
from api_service.routers.parsing import parsing_router

service_router = APIRouter(prefix="/service", dependencies=[Depends(current_super_user)])
service_router.include_router(printer_router)
service_router.include_router(vendor_router)
service_router.include_router(vendor_search_line_router)

service_router.include_router(parsing_router)

service_router.include_router(reward_range_router)
service_router.include_router(hub_router)
service_router.include_router(hubstock_router)
service_router.include_router(comparison_router)
