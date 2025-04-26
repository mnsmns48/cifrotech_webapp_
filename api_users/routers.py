from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer


from api_users.backend import authentication_backend
from api_users.dependencies.fastapi_users_dep import fastapi_users
from api_users.schemas import UserRead, UserCreate

http_bearer = HTTPBearer(auto_error=False)
auth_api_router = APIRouter(dependencies=[Depends(http_bearer)])

auth_router = APIRouter(tags=['Auth'])
auth_router.include_router(fastapi_users.get_auth_router(authentication_backend))
auth_router.include_router(fastapi_users.get_register_router(UserRead, UserCreate))
users_router = APIRouter(tags=['Users'], prefix='/users')
users_router.include_router(fastapi_users.get_users_router(UserRead, UserCreate))
users_router.include_router(fastapi_users.get_verify_router(UserRead))
users_router.include_router(fastapi_users.get_reset_password_router())
auth_api_router.include_router(auth_router)
auth_api_router.include_router(users_router)
