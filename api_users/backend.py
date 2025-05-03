import logging

from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi_users.authentication import BearerTransport, CookieTransport, AuthenticationBackend
from fastapi import status

from api_users.dependencies.strategy import get_database_strategy
from config import settings

log = logging.getLogger(__name__)

bearer_transport = BearerTransport(tokenUrl=settings.token.bearer_token_url)
cookie_transport = CookieTransport(cookie_name="access_token", cookie_max_age=settings.token.lifetime_seconds)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.token.bearer_token_url)

authentication_backend = AuthenticationBackend(name="access-tokens-db",
                                               transport=cookie_transport, get_strategy=get_database_strategy)


async def check_authentication(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Not authorized",
                            headers={"WWW-Authenticate": "Bearer"})
