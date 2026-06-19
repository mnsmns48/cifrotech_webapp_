import asyncio
from datetime import datetime, timezone, timedelta
from enum import Enum

from aiohttp import ClientSession, ClientConnectionError, ClientResponseError
from sqlalchemy.ext.asyncio import AsyncSession

from models import VendorApiToken, Vendor


class TokenState(Enum):
    ACCESS_VALID = "access_valid"
    NEED_REFRESH = "need_refresh"
    NEED_LOGIN = "need_login"
    INACTIVE = "inactive"


class AuthResult(Enum):
    OK = "ok"
    REFRESHED = "refreshed"
    NEED_LOGIN = "need_login"
    INVALID_CREDENTIALS = "invalid_credentials"
    NETWORK_ERROR = "network_error"
    INACTIVE = "inactive"


class TokenStateService:
    @staticmethod
    def check_state(vendor) -> TokenState:
        token = vendor.api_token
        if token is None:
            return TokenState.NEED_LOGIN
        if token.is_active is False:
            return TokenState.INACTIVE
        now = datetime.now(timezone.utc)
        if token.refresh_expires_at is None or token.refresh_expires_at <= now:
            return TokenState.NEED_LOGIN
        if token.access_expires_at and token.access_expires_at > now:
            return TokenState.ACCESS_VALID
        return TokenState.NEED_REFRESH


class LoginService:

    def __init__(self, http_client: ClientSession):
        self.http = http_client

    async def login(self, vendor, session: AsyncSession) -> AuthResult:
        try:
            url = f"{vendor.source}/api/v1/auth/token"
            response = await self.http.post(url, json={"login": vendor.login, "password": vendor.password}, timeout=10)
        except (ClientConnectionError, ClientResponseError, asyncio.TimeoutError):
            return AuthResult.NETWORK_ERROR

        if response.status == 401:
            return AuthResult.INVALID_CREDENTIALS

        data = await response.json()
        now = datetime.now(timezone.utc)

        token = vendor.api_token or VendorApiToken()
        token.access_token = data["accessToken"]
        token.refresh_token = data["refreshToken"]
        token.access_expires_at = now + timedelta(minutes=15)
        token.refresh_expires_at = now + timedelta(days=14)
        token.last_auth_at = now
        token.is_active = True

        session.add(token)
        vendor.api_token = token
        await session.commit()

        return AuthResult.OK


class RefreshService:
    def __init__(self, http_client: ClientSession):
        self.http = http_client

    async def refresh(self, vendor: Vendor, session: AsyncSession):
        token = vendor.api_token
        url = f"{vendor.source}/api/v1/auth/refresh"
        try:
            response = await self.http.post(url, json={"refreshToken": token.refresh_token}, timeout=5)
            if response.status != 200:
                return AuthResult.INVALID_CREDENTIALS
            data = await response.json()
            if "accessToken" not in data or "refreshToken" not in data:
                return AuthResult.NETWORK_ERROR

            now = datetime.now(timezone.utc)
            token.access_token = data["accessToken"]
            token.refresh_token = data["refreshToken"]
            token.access_expires_at = now + timedelta(seconds=data["expiresIn"])
            token.refresh_expires_at = now + timedelta(seconds=data["refreshExpiresIn"])
            token.last_auth_at = now
            await session.commit()
            return AuthResult.OK

        except (ClientConnectionError, ClientResponseError, asyncio.TimeoutError):
            return AuthResult.NETWORK_ERROR


class AuthService:
    def __init__(self, token_state: TokenStateService, login_service: LoginService, refresh_service: RefreshService):
        self.state = token_state
        self.login_service = login_service
        self.refresh_service = refresh_service

    async def ensure_valid_tokens(self, vendor, session: AsyncSession) -> AuthResult:
        token = vendor.api_token

        if token is None or not token.is_active:
            return await self.login_service.login(vendor, session)

        now = datetime.now(timezone.utc)
        remaining = (token.access_expires_at - now).total_seconds()
        if remaining < 600:
            refreshed = await self.refresh_service.refresh(vendor, session)
            if refreshed == AuthResult.OK:
                return AuthResult.OK

            logged = await self.login_service.login(vendor, session)
            return logged

        state = self.state.check_state(vendor)

        if state == TokenState.INACTIVE:
            return AuthResult.INACTIVE

        if state == TokenState.ACCESS_VALID:
            return AuthResult.OK

        if state == TokenState.NEED_REFRESH:
            return await self.refresh_service.refresh(vendor, session)

        if state == TokenState.NEED_LOGIN:
            return await self.login_service.login(vendor, session)

        return AuthResult.NETWORK_ERROR

    async def force_login(self, vendor, session: AsyncSession) -> AuthResult:
        return await self.login_service.login(vendor, session)

    @staticmethod
    def get_status(vendor):
        token = vendor.api_token

        if token is None:
            return {"integration_status": "needs_login", "has_tokens": False}
        now = datetime.now(timezone.utc)

        return {"integration_status": "ok",
                "access_expires_in": (token.access_expires_at - now).total_seconds(),
                "refresh_expires_in": (token.refresh_expires_at - now).total_seconds(),
                "last_auth_at": token.last_auth_at,
                "has_tokens": True,
                "is_active": token.is_active}
