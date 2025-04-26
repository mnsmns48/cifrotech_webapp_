from typing import TYPE_CHECKING, Optional
from fastapi_users import IntegerIDMixin, BaseUserManager
from api_users.backend import log
from config import settings
from models import User
from var_types import var_types

if TYPE_CHECKING:
    from fastapi.requests import Request


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
