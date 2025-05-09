from fastapi import APIRouter, Depends
from fastapi.requests import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.schemas import VendorSearchLineSchema
from engine import db
from models.vendor import Vendor_search_line

vendor_search_line_router = APIRouter(tags=['Service-Vendors-Search-Line'])


@vendor_search_line_router.get("/get_vsl/{vendor_id}")
async def get_vendors(request: Request, vendor_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    result = await session.execute(
        select(Vendor_search_line).filter(Vendor_search_line.vendor_id == vendor_id).order_by(Vendor_search_line.id))
    vendor_search_lines = list()
    for vsl in result.scalars().all():
        vendor_search_lines.append(VendorSearchLineSchema.cls_validate(vsl))
    return {"vsl": vendor_search_lines}
