from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud_attributes import fetch_all_attribute_keys, create_attribute_key, update_attribute_key, \
    delete_attribute_key, fetch_all_attribute_values_with_keys, create_attribute, update_attribute_value, \
    delete_attribute_value
from api_service.schemas.attribute_schemas import CreateAttribute, UpdateAttribute
from engine import db

attributes_router = APIRouter(tags=['Attributes'])


@attributes_router.get("/attributes/get_attr_keys")
async def get_hub_levels(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await fetch_all_attribute_keys(session)


@attributes_router.post("/attributes/create_attr_key")
async def create_attr_key(key: str, session: AsyncSession = Depends(db.scoped_session_dependency)):
    new_key = await create_attribute_key(session, key)
    return {"status": "ok", "created": new_key}


@attributes_router.put("/attributes/update_attr_key")
async def update_attr_key(key_id: int, new_key: str,
                          session: AsyncSession = Depends(db.scoped_session_dependency)):
    updated = await update_attribute_key(session, key_id, new_key)

    if updated is None:
        raise HTTPException(status_code=404, detail="Key not found")

    return {"status": "ok", "updated": updated}


@attributes_router.delete("/attributes/delete_attr_key")
async def delete_attr_key(key_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    result = await delete_attribute_key(session, key_id)
    if result:
        return {"status": "ok", "deleted_id": key_id}


@attributes_router.get("/attributes/get_attr_values")
async def get_attr_keys_and_values(session: AsyncSession = Depends(db.scoped_session_dependency)):
    keys = await fetch_all_attribute_keys(session)
    values = await fetch_all_attribute_values_with_keys(session)
    result = {"keys": [], "values": []}

    for k in keys:
        result["keys"].append({"id": k.id, "key": k.key})

    for v in values:
        result["values"].append(v)

    return result


@attributes_router.post("/attributes/create_attribute")
async def create_attribute_item(payload: CreateAttribute,
                                session: AsyncSession = Depends(db.scoped_session_dependency)):
    new_attribute = await create_attribute(session, payload)
    return {"id": new_attribute.id,
            "attr_key_id": new_attribute.attr_key_id,
            "value": new_attribute.value,
            "alias": new_attribute.alias}


@attributes_router.put("/attributes/update_attribute")
async def update_attribute_item(payload: UpdateAttribute,
                                session: AsyncSession = Depends(db.scoped_session_dependency)):
    updated = await update_attribute_value(session, value_id=payload.id,
                                           new_value=payload.attribute_name, new_alias=payload.alias)

    return {
        "id": updated.id,
        "attr_key_id": updated.attr_key_id,
        "value": updated.value,
        "alias": updated.alias
    }


@attributes_router.delete("/attributes/delete_attribute")
async def delete_attribute_item(value_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    result = await delete_attribute_value(session, value_id)
    if result:
        return {"status": "ok", "deleted_id": value_id}
