import logging
from typing import Optional, TYPE_CHECKING

from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi_users import IntegerIDMixin, BaseUserManager
from fastapi_users.authentication import BearerTransport, CookieTransport
from fastapi import status
from config import settings
from models import User
from var_types import var_types

if TYPE_CHECKING:
    from fastapi import Request

log = logging.getLogger(__name__)

bearer_transport = BearerTransport(tokenUrl=settings.token.bearer_token_url)
cookie_transport = CookieTransport(cookie_name="access_token", cookie_max_age=settings.token.lifetime_seconds)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.token.bearer_token_url)


async def check_authentication(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Not authorized",
                            headers={"WWW-Authenticate": "Bearer"})


class UserManager(IntegerIDMixin, BaseUserManager[User, var_types.UserIdType]):
    reset_password_token_secret = settings.token.reset_password_token_secret
    verification_token_secret = settings.token.verification_token_secret

    async def on_after_register(self, user: User, request: Optional["Request"] = None):
        log.warning("User %r has registered.", user.id)
        # await send_new_user_notification(user)

    async def on_after_request_verify(self, user: User, token: str, request: Optional["Request"] = None):
        log.warning("Verification requested for user %r. Verification token: %r", user.id, token)

    async def on_after_forgot_password(self, user: User, token: str, request: Optional["Request"] = None):
        log.warning("User %r has forgot their password. Reset token: %r", user.id, token)
