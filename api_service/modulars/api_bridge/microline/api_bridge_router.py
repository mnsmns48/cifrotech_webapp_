from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.api_bridge.microline.schemas import AddVendorApiSearch, VendorApiSearchResponse, \
    DeleteVendorApiSearch, VendorApiSearchDeleteResponse, ApiSearchVSLResponse
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


@api_bridge_router.get("/api_bridge/vendor_api_search_line_link/{api_search_id}", response_model=ApiSearchVSLResponse)
async def get_vendor_api_search_line_link(api_search_id: int, session: AsyncSession = Depends(db.session_dependency)):
    return await ApiBridgeService.get_vendor_api_search_line_link(api_search_id, session)


