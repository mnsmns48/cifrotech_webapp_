from fastapi import Request, Depends, HTTPException, APIRouter
from sqlalchemy import select

from api_service.schemas import VendorSchema
from api_service.utils import update_instance_fields
from engine import db
from models import Vendor
from sqlalchemy.ext.asyncio import AsyncSession

vendor_router = APIRouter(tags=['Service-Vendors'])


@vendor_router.get("/vendors")
async def get_vendors(request: Request, session: AsyncSession = Depends(db.scoped_session_dependency)):
    result = await session.execute(select(Vendor).order_by(Vendor.id))
    vendors = list()
    for vendor in result.scalars().all():
        vendors.append(VendorSchema.cls_validate(vendor))
    return {"vendors": vendors}


@vendor_router.post("/vendors")
async def add_vendor(data: VendorSchema, session: AsyncSession = Depends(db.scoped_session_dependency)):
    new_vendor = Vendor(**VendorSchema.cls_validate(data, exclude_id=True))
    session.add(new_vendor)
    await session.commit()
    await session.refresh(new_vendor)
    return {"result": "Vendor added", "vendor": VendorSchema.cls_validate(new_vendor)}


@vendor_router.put("/vendors/{vendor_id}")
async def update_vendor(vendor_id: int, vendor_data: VendorSchema,
                        session: AsyncSession = Depends(db.scoped_session_dependency)):
    vendor = await session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    update_data = VendorSchema.cls_validate(vendor_data, exclude_id=True)
    await update_instance_fields(vendor, update_data, session)
    return {"result": f"Vendor {vendor.name} updated"}


@vendor_router.delete("/vendors/{vendor_id}")
async def delete_vendor(vendor_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    vendor = await session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    await session.delete(vendor)
    await session.commit()
    return {"result": f"Vendor {vendor.name} deleted"}
