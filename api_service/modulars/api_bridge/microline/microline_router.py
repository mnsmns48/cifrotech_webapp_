import asyncio
import json
import time

from aiohttp import ClientConnectorError, ClientConnectionError, ClientResponseError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.api_bridge.microline.dependencies import get_microline_service
from api_service.modulars.api_bridge.microline.scheme import LoginRequest, ProductsFromApiResponse
from api_service.modulars.api_bridge.microline.service import MicrolineService
from api_service.modulars.api_bridge.token_services import AuthService, AuthResult
from config import redis_session
from engine import db
from models import Vendor, VendorApiSearch

microline_router = APIRouter(tags=['API Integration'], prefix='/microline')


async def ensure_vendor_ready(vendor_id: int, session: AsyncSession, service: MicrolineService):
    vendor = await session.get(Vendor, vendor_id)
    if vendor is None:
        return None, {"status": "vendor_not_found"}

    try:
        result = await service.auth.ensure_valid_tokens(vendor, session)
        if result != AuthResult.OK:
            return None, {"status": "auth_error"}
    except (ClientConnectorError, ClientConnectionError, asyncio.TimeoutError):
        return None, {"status": "auth_error"}

    return vendor, None


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
    vendor, error = await ensure_vendor_ready(vendor_id, session, service)
    if error:
        return error

    categories = await service.client.get_categories(vendor, parentId)
    return {"status": "ok", "categories": categories}


async def send_progress(redis, progress_id: str, message: dict):
    if not progress_id:
        return
    await redis.publish(progress_id, json.dumps(message))


@microline_router.get("/vendors/{vendor_id}/products", response_model=ProductsFromApiResponse)
async def get_products(vendor_id: int,
                       categoryId: int,
                       contractorId: int,
                       deliveryLocationId: int,
                       progress: str | None = None,
                       limit: int = 120,
                       redis=Depends(redis_session),
                       session: AsyncSession = Depends(db.session_dependency),
                       service: MicrolineService = Depends(get_microline_service)):
    vendor = await session.get(Vendor, vendor_id)
    if vendor is None:
        return {"status": "vendor_not_found"}

    result = await service.auth.ensure_valid_tokens(vendor, session)
    if result != AuthResult.OK:
        return {"status": "auth_error"}

    start_time = time.perf_counter()
    first_page = await service.client.get_products(vendor, contractor_id=contractorId,
                                                   delivery_location_id=deliveryLocationId,
                                                   category_id=categoryId,
                                                   page=1,
                                                   limit=limit)

    items = first_page.get("items", [])
    total = first_page.get("total", None)

    if not total:
        total = len(items)
    pages = (total + limit - 1) // limit
    percent = 0 if total == 0 else round((len(items) / total) * 100, 2)
    await send_progress(redis, progress, {"page": 1,
                                          "pages": pages,
                                          "received": len(items),
                                          "total_items": len(items),
                                          "percent": percent,
                                          "eta": None})

    all_items = list(items)
    for page in range(2, pages + 1):
        data = await service.client.get_products(vendor, contractor_id=contractorId,
                                                 delivery_location_id=deliveryLocationId,
                                                 category_id=categoryId,
                                                 page=page,
                                                 limit=limit)
        page_items = data.get("items", [])
        all_items.extend(page_items)
        elapsed = time.perf_counter() - start_time
        avg_page_time = elapsed / page
        eta = avg_page_time * (pages - page)
        percent = 0 if total == 0 else round((len(all_items) / total) * 100, 2)
        await send_progress(redis, progress, {"page": page, "pages": pages, "received": len(page_items),
                                              "total_items": len(all_items),
                                              "percent": percent,
                                              "eta": round(eta, 1)})
    await send_progress(redis, progress, {"status": "END"})
    all_items.sort(key=lambda x: float(x.get("price", 0)))
    elapsed = time.perf_counter() - start_time

    exists = await session.scalar(
        select(VendorApiSearch.id)
        .where(VendorApiSearch.vendor_id == vendor_id)
        .where(VendorApiSearch.category_id == categoryId)
    )

    already_exists = exists is not None
    return ProductsFromApiResponse(status="ok", total=len(all_items),
                                   exec_time=round(elapsed, 1), already_exists=already_exists, products=all_items)


@microline_router.get("/vendors/{vendor_id}/access-check")
async def check_access(vendor_id: int,
                       session: AsyncSession = Depends(db.session_dependency),
                       service: MicrolineService = Depends(get_microline_service)):
    vendor, error = await ensure_vendor_ready(vendor_id, session, service)
    if error:
        return error

    contractors = await service.client.get_contractors(vendor)
    result = dict()

    for line in contractors:
        if line.get("contractorId"):
            result.update({"contractorId": line.get("contractorId"), "status": "ok"})
            for delivery_line in line.get("deliveryLocations", []):
                result.update({"deliveryLocationId": delivery_line.get("deliveryLocationId")})

    return result
