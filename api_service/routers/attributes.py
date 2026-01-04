from typing import List
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud_attributes import fetch_all_attribute_keys, create_attribute_key, update_attribute_key, \
    delete_attribute_key, fetch_all_attribute_values_with_keys, create_attribute, update_attribute_value, \
    delete_attribute_value, fetch_types_with_rules, fetch_all_brands, add_type_dependency_db, delete_type_dependency_db, \
    delete_attribute_brand_link_db, add_attribute_brand_link_db, fetch_all_types, load_model_attribute_options_db, \
    product_dependencies_db, add_product_attribute_value_option, delete_product_attribute_value_option

from api_service.schemas import CreateAttribute, UpdateAttribute, TypesDependenciesResponse, TypeDependencyLink, \
    AttributeBrandRuleLink, ProductFeaturesAttributeOptions, Types, ModelAttributesRequest, ModelAttributesResponse, \
    AttributeModelOptionLink
from engine import db
from models.attributes import OverrideType

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


@attributes_router.get("/attributes/get_types_dependencies", response_model=TypesDependenciesResponse)
async def get_type_dependencies(session: AsyncSession = Depends(db.scoped_session_dependency)):
    types_map = await fetch_types_with_rules(session)
    keys = await fetch_all_attribute_keys(session)
    brands = await fetch_all_brands(session)
    return TypesDependenciesResponse(types_map=types_map, keys=keys, brands=brands)


@attributes_router.post("/attributes/add_types_dependencies")
async def add_type_dependencies(payload: TypeDependencyLink,
                                session: AsyncSession = Depends(db.scoped_session_dependency)):
    link = await add_type_dependency_db(session=session, type_id=payload.type_id, attr_key_id=payload.attr_key_id)
    return TypeDependencyLink(type_id=link.product_type_id, attr_key_id=link.attr_key_id)


@attributes_router.delete("/attributes/delete_types_dependencies")
async def delete_type_dependencies(
        type_id: int, attr_key_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    deleted = await delete_type_dependency_db(session=session, type_id=type_id, attr_key_id=attr_key_id)
    return TypeDependencyLink(**deleted)


@attributes_router.post("/attributes/add_attribute_brand_link")
async def add_attribute_brand_link(payload: AttributeBrandRuleLink,
                                   session: AsyncSession = Depends(db.scoped_session_dependency)):
    link = await add_attribute_brand_link_db(session=session, data=payload)
    return link


@attributes_router.delete("/attributes/delete_attribute_brand_link")
async def delete_attribute_brand_link(product_type_id: int, brand_id: int, attr_key_id: int, rule_type: OverrideType,
                                      session: AsyncSession = Depends(db.scoped_session_dependency)):
    obj = AttributeBrandRuleLink(product_type_id=product_type_id, brand_id=brand_id, attr_key_id=attr_key_id,
                                 rule_type=rule_type)
    deleted = await delete_attribute_brand_link_db(session=session, obj=obj)
    return deleted


@attributes_router.get("/attributes/get_all_types", response_model=List[Types])
async def get_model_dependencies(session: AsyncSession = Depends(db.scoped_session_dependency)):
    types = await fetch_all_types(session)
    return list(types)


@attributes_router.get("/attributes/load_model_attribute_options/{product_type_id}",
                       response_model=List[ProductFeaturesAttributeOptions])
async def load_model_attribute_options(product_type_id: int,
                                       session: AsyncSession = Depends(db.scoped_session_dependency)):
    items = await load_model_attribute_options_db(session=session, product_type_id=product_type_id)
    return items


@attributes_router.post("/attributes/model_attributes_request", response_model=ModelAttributesResponse)
async def product_dependencies_scheme(payload: ModelAttributesRequest,
                                      session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await product_dependencies_db(session=session, payload=payload)


@attributes_router.post("/attributes/add_product_attribute_value_option_link")
async def add_product_attribute_value_option_link(payload: AttributeModelOptionLink,
                                                  session: AsyncSession = Depends(db.scoped_session_dependency)):
    result = await add_product_attribute_value_option(payload=payload, session=session)
    return result


@attributes_router.post("/attributes/delete_product_attribute_value_option_link")
async def delete_product_attribute_value_option_link(payload: AttributeModelOptionLink,
                                                     session: AsyncSession = Depends(db.scoped_session_dependency)):
    result = await delete_product_attribute_value_option(payload=payload, session=session)
    return result
