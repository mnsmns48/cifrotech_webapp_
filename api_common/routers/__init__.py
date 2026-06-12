from fastapi import APIRouter

from api_common.routers.description_router import description_router
from api_common.routers.progress import progress_router

general_router = APIRouter(tags=['General'])

general_router.include_router(progress_router)
general_router.include_router(description_router)
