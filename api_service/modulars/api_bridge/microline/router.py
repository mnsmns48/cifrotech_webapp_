import asyncio
import time
from aiohttp import ClientConnectorError, ClientConnectionError, ClientResponseError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import result_tuple
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.api_bridge.microline.dependencies import get_microline_service
from api_service.modulars.api_bridge.microline.scheme import LoginRequest
from api_service.modulars.api_bridge.microline.service import MicrolineService
from api_service.modulars.api_bridge.token_services import AuthService, AuthResult
from engine import db
from models import Vendor

microline_router = APIRouter(tags=['API Integration'], prefix='/microline')


@microline_router.get("/vendors/{vendor_id}/integration-status")
async def integration_status(vendor_id: int,
                             session: AsyncSession = Depends(db.session_dependency),
                             service: MicrolineService = Depends(get_microline_service)):
    vendor = await session.get(Vendor, vendor_id)
    if vendor is None:
        raise HTTPException(404, "Vendor not found")

    if vendor.api_token is None:
        result = await service.auth.force_login(vendor, session)
        if result != AuthResult.OK:
            raise HTTPException(401, "Auto-login failed")

    status = AuthService.get_status(vendor)

    if status["integration_status"] == "needs_login":
        result = await service.auth.force_login(vendor, session)
        if result != AuthResult.OK:
            raise HTTPException(401, "Auto-login failed")
        status = AuthService.get_status(vendor)

    return status


@microline_router.post("/vendors/{vendor_id}/login")
async def login_vendor(vendor_id: int,
                       body: LoginRequest,
                       session: AsyncSession = Depends(db.session_dependency),
                       service: MicrolineService = Depends(get_microline_service)):
    vendor = await session.get(Vendor, vendor_id)
    if vendor is None:
        raise HTTPException(404, "Vendor not found")
    vendor.login = body.login
    vendor.password = body.password
    result = await service.auth.force_login(vendor, session)
    if result == AuthResult.INVALID_CREDENTIALS:
        raise HTTPException(401, "Invalid credentials")
    if result == AuthResult.NETWORK_ERROR:
        raise HTTPException(503, "Auth network error")
    return AuthService.get_status(vendor)


@microline_router.get("/vendors/{vendor_id}/ping")
async def ping_vendor(vendor_id: int,
                      session: AsyncSession = Depends(db.session_dependency),
                      service: MicrolineService = Depends(get_microline_service)):
    vendor = await session.get(Vendor, vendor_id)

    result = await service.auth.ensure_valid_tokens(vendor, session)
    if result not in (AuthResult.OK, AuthResult.REFRESHED):
        return {"status": "auth_error"}
    try:
        start = time.perf_counter()
        await asyncio.wait_for(service.client.get_me(vendor), timeout=3)
        ping_ms = int((time.perf_counter() - start) * 1000)
        return {"status": "ok", "ping": ping_ms}

    except (ClientConnectorError, ClientConnectionError, asyncio.TimeoutError):
        return {"status": "network_error"}

    except ClientResponseError as e:
        if e.status == 401:
            return {"status": "auth_error"}
        return {"status": "network_error"}


@microline_router.get("/vendors/{vendor_id}/me")
async def get_me(vendor_id: int,
                 session: AsyncSession = Depends(db.session_dependency),
                 service: MicrolineService = Depends(get_microline_service)):
    return await service.get_me(vendor_id, session)


@microline_router.get("/vendors/{vendor_id}/categories")
async def get_categories(vendor_id: int,
                         parentId: int | None = None,
                         session: AsyncSession = Depends(db.session_dependency),
                         service: MicrolineService = Depends(get_microline_service)):
    vendor = await session.get(Vendor, vendor_id)
    if vendor is None:
        return {"status": "vendor_not_found"}

    try:
        result = await service.auth.ensure_valid_tokens(vendor, session)
        if result != AuthResult.OK:
            return {"status": "auth_error"}

    except (ClientConnectorError, ClientConnectionError, asyncio.TimeoutError):
        return {"status": "auth_error"}

    categories = await service.client.get_categories(vendor, parentId)
    return {"status": "ok", "categories": categories}


@microline_router.get("/vendors/{vendor_id}/products")
async def get_products(vendor_id: int, categoryId: int, contractorId: int, deliveryLocationId: int,
                       page: int = 1, limit: int = 200, auto: bool = False,
                       session: AsyncSession = Depends(db.session_dependency),
                       service: MicrolineService = Depends(get_microline_service)):
    vendor = await session.get(Vendor, vendor_id)
    await service._ensure_auth(vendor, session)
    if auto:
        all_items = list()
        current_page = 1
        while True:
            try:
                data = await service.client.get_products(
                    vendor, contractor_id=contractorId, delivery_location_id=deliveryLocationId,
                    category_id=categoryId, page=current_page, limit=limit)
            except asyncio.TimeoutError:
                return {"status": "timeout", "message": "Vendor API too slow"}

            items = data.get("items", [])
            all_items.extend(items)
            if len(items) < limit:
                break
            current_page += 1

        return {"status": "ok", "total": len(all_items), "products": all_items}

    try:
        data = await service.client.get_products(vendor,
                                                 contractor_id=contractorId,
                                                 delivery_location_id=deliveryLocationId,
                                                 category_id=categoryId,
                                                 page=page,
                                                 limit=limit)
    except asyncio.TimeoutError:
        return {"status": "timeout", "message": "Vendor API too slow"}

    return {"status": "ok", "products": data}


@microline_router.get("/vendors/{vendor_id}/access-check")
async def check_access(
        vendor_id: int,
        session: AsyncSession = Depends(db.session_dependency),
        service: MicrolineService = Depends(get_microline_service)
):
    vendor = await session.get(Vendor, vendor_id)
    if vendor is None:
        return {"status": "vendor_not_found"}

    try:
        result = await service.auth.ensure_valid_tokens(vendor, session)
        if result != AuthResult.OK:
            return {"status": "auth_error"}
    except (ClientConnectorError, ClientConnectionError, asyncio.TimeoutError):
        return {"status": "auth_error"}

    contractors = await service.client.get_contractors(vendor)
    result = dict()

    for line in contractors:
        if line.get("contractorId"):
            result.update(
                {"contractorId": line.get("contractorId"), "status": "ok"}
            )
            for delivery_line in line.get("deliveryLocations", []):
                result.update(
                    {"deliveryLocationId": delivery_line.get("deliveryLocationId")}
                )

    return result
