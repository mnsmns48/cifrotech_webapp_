from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
from sqlalchemy import select

from api_service.schemas import VSLScheme, VSLSchemeWithBrandsCreate, VSLSchemeWithBrands, BrandModel, \
    VendorApiSearchLinkScheme
from api_service.utils import update_instance_fields
from engine import db
from models import ProductBrand
from models.vendor import VendorSearchLine, VendorSearchLineBrandLink, VendorApiSearchLineLink
from sqlalchemy.ext.asyncio import AsyncSession

vendor_search_line_router = APIRouter(tags=['Service-Vendors-Search-Line'])


@vendor_search_line_router.get("/get_vsl/{vendor_id}")
async def get_vendors(request: Request, vendor_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    result = await session.execute(
        select(VendorSearchLine).filter(VendorSearchLine.vendor_id == vendor_id).order_by(VendorSearchLine.id))
    vendor_search_lines = list()
    for vsl in result.scalars().all():
        vendor_search_lines.append(VSLScheme.cls_validate(vsl))
    return {"vsl": vendor_search_lines}


@vendor_search_line_router.post("/create_vsl/{vendor_id}")
async def create_vendor_search_line(request: Request, vendor_id: int, vsl_data: VSLScheme,
                                    session: AsyncSession = Depends(db.scoped_session_dependency)):
    existing_vsl = await session.execute(
        select(VendorSearchLine).where(
            (VendorSearchLine.title == vsl_data.title) | (VendorSearchLine.url == vsl_data.url)))
    existing_vsl = existing_vsl.scalar()
    if existing_vsl:
        raise HTTPException(status_code=409, detail="Vendor Search Line with this title or URL already exists")
    new_vsl = VendorSearchLine(**VSLScheme.cls_validate(vsl_data, exclude_id=True))
    session.add(new_vsl)
    await session.commit()
    await session.refresh(new_vsl)
    return {"vsl": VSLScheme.cls_validate(new_vsl)}


@vendor_search_line_router.put("/update_vsl/{vsl_id}")
async def update_vendor_search_line(request: Request, vsl_id: int, vsl_data: VSLScheme,
                                    session: AsyncSession = Depends(db.scoped_session_dependency)):
    vsl = await session.get(VendorSearchLine, vsl_id)
    if not vsl:
        raise HTTPException(status_code=404, detail="VendorSearchLine not found")
    update_data = VSLScheme.cls_validate(vsl_data, exclude_id=True)
    await update_instance_fields(vsl, update_data, session)
    return {"result": f"Vendor Search Line {vsl.id} updated"}


@vendor_search_line_router.delete("/delete_vsl/{vsl_id}")
async def delete_vendor_search_line(vsl_id: int,
                                    session: AsyncSession = Depends(db.scoped_session_dependency)):
    vsl = await session.get(VendorSearchLine, vsl_id)
    if not vsl:
        raise HTTPException(status_code=404, detail="Vendor Search Line not found")
    try:
        await session.delete(vsl)
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return {"result": f"Vendor Search Line {vsl_id} deleted"}


@vendor_search_line_router.post("/create_vsl_with_brand", response_model=VSLSchemeWithBrands)
async def create_vsl_with_brand(payload: VSLSchemeWithBrandsCreate,
                                session: AsyncSession = Depends(db.scoped_session_dependency)):
    errors = list()

    title = (payload.title or "").strip()
    if not title:
        errors.append("Title не может быть пустым")

    else:
        stmt_title = select(VendorSearchLine).where(VendorSearchLine.vendor_id == payload.vendor_id,
                                                    VendorSearchLine.title == title)
        exists_title = await session.execute(stmt_title)
        if exists_title.scalar_one_or_none():
            errors.append("такой Title уже есть")

    url = (payload.url or "").strip()
    if not url:
        errors.append("URL не может быть пустым")

    else:
        stmt_url = select(VendorSearchLine).where(VendorSearchLine.vendor_id == payload.vendor_id,
                                                  VendorSearchLine.url == url)
        exists_url = await session.execute(stmt_url)
        if exists_url.scalar_one_or_none():
            errors.append("такой URL уже есть")

    if errors:
        raise HTTPException(status_code=400, detail=", ".join(errors))

    new_vsl = VendorSearchLine(vendor_id=payload.vendor_id, title=title, url=url)

    session.add(new_vsl)
    await session.flush()

    if payload.brands:
        for brand in payload.brands:
            session.add(VendorSearchLineBrandLink(vsl_id=new_vsl.id, brand_id=brand.id))

    await session.commit()

    return VSLSchemeWithBrands(id=new_vsl.id, vendor_id=new_vsl.vendor_id, title=new_vsl.title,
                               url=new_vsl.url, dt_parsed=new_vsl.dt_parsed, brands=payload.brands)


@vendor_search_line_router.put("/update_vsl_with_brand", response_model=VSLSchemeWithBrands)
async def update_vsl_with_brand(payload: VSLSchemeWithBrands,
                                session: AsyncSession = Depends(db.scoped_session_dependency)) -> VSLSchemeWithBrands:
    vsl = await session.get(VendorSearchLine, payload.id)
    if not vsl:
        raise HTTPException(status_code=404, detail="Vendor Search Line not found")

    errors = list()

    title = (payload.title or "").strip()
    if not title:
        errors.append("Title cannot be empty")
    else:
        stmt_title = select(VendorSearchLine).where(VendorSearchLine.vendor_id == payload.vendor_id,
                                                    VendorSearchLine.title == title,
                                                    VendorSearchLine.id != payload.id)
        exists_title = await session.execute(stmt_title)
        if exists_title.scalar_one_or_none():
            errors.append("Title already exists")

    url = (payload.url or "").strip()
    if not url:
        errors.append("URL cannot be empty")
    else:
        stmt_url = select(VendorSearchLine).where(VendorSearchLine.vendor_id == payload.vendor_id,
                                                  VendorSearchLine.url == url,
                                                  VendorSearchLine.id != payload.id)
        exists_url = await session.execute(stmt_url)
        if exists_url.scalar_one_or_none():
            errors.append("URL already exists")

    if errors:
        raise HTTPException(status_code=400, detail=", ".join(errors))

    changed = False

    if vsl.title != title:
        vsl.title = title
        changed = True

    if vsl.url != url:
        vsl.url = url
        changed = True

    stmt_links = select(VendorSearchLineBrandLink).where(VendorSearchLineBrandLink.vsl_id == payload.id)
    rows_links = await session.execute(stmt_links)
    existing_links = rows_links.scalars().all()

    existing_brand_ids = {link.brand_id for link in existing_links}
    new_brand_ids = {b.id for b in (payload.brands or [])}

    for link in existing_links:
        if link.brand_id not in new_brand_ids:
            await session.delete(link)
            changed = True

    for brand_id in new_brand_ids:
        if brand_id not in existing_brand_ids:
            session.add(VendorSearchLineBrandLink(vsl_id=payload.id, brand_id=brand_id))
            changed = True

    if changed:
        await session.commit()
        await session.refresh(vsl)

    stmt_brands = (
        select(ProductBrand).join(VendorSearchLineBrandLink, VendorSearchLineBrandLink.brand_id == ProductBrand.id)
        .where(VendorSearchLineBrandLink.vsl_id == payload.id))
    rows_brands = await session.execute(stmt_brands)
    brands = [BrandModel.model_validate(b) for b in rows_brands.scalars().all()]

    return VSLSchemeWithBrands.model_validate({"id": vsl.id, "vendor_id": vsl.vendor_id,
                                               "title": vsl.title, "url": vsl.url,
                                               "dt_parsed": vsl.dt_parsed, "brands": brands})


@vendor_search_line_router.post("/add_link_vsl_api_search")
async def add_link_vsl_api_search(payload: VendorApiSearchLinkScheme,
                                  session: AsyncSession = Depends(db.scoped_session_dependency)):
    stmt = select(VendorApiSearchLineLink).where(VendorApiSearchLineLink.api_search_id == payload.api_search_id,
                                                 VendorApiSearchLineLink.vsl_id == payload.vsl_id)
    exists = await session.execute(stmt)
    if exists.scalar_one_or_none():
        return {"result": "already_exists"}

    link = VendorApiSearchLineLink(api_search_id=payload.api_search_id, vsl_id=payload.vsl_id)

    session.add(link)
    await session.commit()
    return {"result": "added"}


@vendor_search_line_router.delete("/remove_link_vsl_api_search")
async def remove_link_vsl_api_search(payload: VendorApiSearchLinkScheme,
                                     session: AsyncSession = Depends(db.scoped_session_dependency)):
    stmt = select(VendorApiSearchLineLink).where(VendorApiSearchLineLink.api_search_id == payload.api_search_id,
                                                 VendorApiSearchLineLink.vsl_id == payload.vsl_id)
    rows = await session.execute(stmt)
    link = rows.scalar_one_or_none()

    if not link:
        return {"result": "not_found"}

    await session.delete(link)
    await session.commit()
    return {"result": "removed"}
