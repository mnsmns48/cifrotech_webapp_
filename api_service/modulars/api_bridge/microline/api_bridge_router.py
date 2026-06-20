from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.api_bridge.microline.scheme import AddVendorApiSearch, VendorApiSearchResponse, \
    DeleteVendorApiSearch, VendorApiSearchDeleteResponse
from api_service.modulars.api_bridge.microline.service import ApiBridgeService
from engine import db

api_bridge_router = APIRouter()


@api_bridge_router.post("/api_bridge/add_vendor_api_search", response_model=VendorApiSearchResponse)
async def bridge_add_vendor_api_search(payload: AddVendorApiSearch,
                                       session: AsyncSession = Depends(
                                           db.session_dependency)) -> VendorApiSearchResponse:
    return await ApiBridgeService.bridge_add_vendor_api_search(payload, session)


@api_bridge_router.post("/api_bridge/delete_vendor_api_search", response_model=VendorApiSearchDeleteResponse)
async def bridge_delete_vendor_api_search(payload: DeleteVendorApiSearch,
                                          session: AsyncSession = Depends(
                                              db.session_dependency)) -> VendorApiSearchDeleteResponse:
    return await ApiBridgeService.bridge_delete_vendor_api_search(payload, session)
