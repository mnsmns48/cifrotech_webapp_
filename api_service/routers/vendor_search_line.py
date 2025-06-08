from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
from sqlalchemy import select

from api_service.schemas import VendorSearchLineSchema
from api_service.utils import update_instance_fields
from engine import db
from models.vendor import VendorSearchLine
from sqlalchemy.ext.asyncio import AsyncSession

vendor_search_line_router = APIRouter(tags=['Service-Vendors-Search-Line'])


@vendor_search_line_router.get("/get_vsl/{vendor_id}")
async def get_vendors(request: Request, vendor_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    result = await session.execute(
        select(VendorSearchLine).filter(VendorSearchLine.vendor_id == vendor_id).order_by(VendorSearchLine.id))
    vendor_search_lines = list()
    for vsl in result.scalars().all():
        vendor_search_lines.append(VendorSearchLineSchema.cls_validate(vsl))
    return {"vsl": vendor_search_lines}


@vendor_search_line_router.post("/create_vsl/{vendor_id}")
async def create_vendor_search_line(request: Request, vendor_id: int, vsl_data: VendorSearchLineSchema,
                                    session: AsyncSession = Depends(db.scoped_session_dependency)):
    existing_vsl = await session.execute(
        select(VendorSearchLine).where(
            (VendorSearchLine.title == vsl_data.title) | (VendorSearchLine.url == vsl_data.url)))
    existing_vsl = existing_vsl.scalar()
    if existing_vsl:
        raise HTTPException(status_code=409, detail="Vendor Search Line with this title or URL already exists")
    new_vsl = VendorSearchLine(**VendorSearchLineSchema.cls_validate(vsl_data, exclude_id=True))
    session.add(new_vsl)
    await session.commit()
    await session.refresh(new_vsl)
    return {"vsl": VendorSearchLineSchema.cls_validate(new_vsl)}


@vendor_search_line_router.put("/update_vsl/{vsl_id}")
async def update_vendor_search_line(request: Request, vsl_id: int, vsl_data: VendorSearchLineSchema,
                                    session: AsyncSession = Depends(db.scoped_session_dependency)):
    vsl = await session.get(VendorSearchLine, vsl_id)
    if not vsl:
        raise HTTPException(status_code=404, detail="VendorSearchLine not found")
    update_data = VendorSearchLineSchema.cls_validate(vsl_data, exclude_id=True)
    await update_instance_fields(vsl, update_data, session)
    return {"result": f"Vendor Search Line {vsl.id} updated"}


@vendor_search_line_router.delete("/delete_vsl/{vsl_id}")
async def delete_vendor_search_line(vsl_id: int,
                                    session: AsyncSession = Depends(db.scoped_session_dependency)):
    vsl = await session.get(VendorSearchLine, vsl_id)
    if not vsl:
        raise HTTPException(status_code=404, detail="Vendor Search Line not found")
    await session.delete(vsl)
    await session.commit()
    return {"result": f"Vendor Search Line {vsl_id} deleted"}
