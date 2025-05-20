from fastapi import APIRouter

from api_general.routers.progress import progress_router

general_router = APIRouter(tags=['General'])

general_router.include_router(progress_router)
