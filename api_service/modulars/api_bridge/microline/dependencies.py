from fastapi import Depends
from aiohttp import ClientSession, ClientTimeout

from api_service.modulars.api_bridge.microline.client import MicrolineClient
from api_service.modulars.api_bridge.microline.service import MicrolineService
from api_service.modulars.api_bridge.token_services import (AuthService,
                                                                 TokenStateService,
                                                                 LoginService,
                                                                 RefreshService)


async def get_http_client():
    timeout = ClientTimeout(total=1000, connect=10, sock_read=1000)

    async with ClientSession(timeout=timeout) as session:
        yield session


async def get_login_service(http: ClientSession = Depends(get_http_client)):
    return LoginService(http)


async def get_refresh_service(http: ClientSession = Depends(get_http_client)):
    return RefreshService(http)


def get_token_state_service():
    return TokenStateService()


async def get_auth_service(token_state: TokenStateService = Depends(get_token_state_service),
                           login_service: LoginService = Depends(get_login_service),
                           refresh_service: RefreshService = Depends(get_refresh_service)):
    return AuthService(token_state, login_service, refresh_service)


async def get_microline_service(http: ClientSession = Depends(get_http_client),
                                auth: AuthService = Depends(get_auth_service)):
    client = MicrolineClient(http)
    return MicrolineService(auth, client)
