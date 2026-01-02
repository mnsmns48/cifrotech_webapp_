from fastapi import HTTPException
from sqlalchemy import select, update, delete, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from starlette import status

from api_service.schemas.attribute_schemas import CreateAttribute, AttributeBrandRuleLink, \
    ProductDependenciesKeysValuesScheme, AttributeValueSchema, AttributeKeySchema, ProductDependenciesSchema, \
    AttributeModelOptionLink
from models import ProductType, AttributeKey, AttributeValue, AttributeLink, AttributeBrandRule, ProductBrand, \
    ProductFeaturesGlobal
from models.attributes import OverrideType, AttributeModelOption


async def fetch_all_attribute_keys(session: AsyncSession):
    execute = await session.execute(select(AttributeKey))
    return execute.scalars().all()


async def create_attribute_key(session: AsyncSession, key: str) -> AttributeKey:
    new_key = AttributeKey(key=key)
    session.add(new_key)
    await session.commit()
    await session.refresh(new_key)
    return new_key


async def update_attribute_key(session: AsyncSession, key_id: int, new_key: str) -> AttributeKey | None:
    result = await session.execute(
        select(AttributeKey).where(AttributeKey.id == key_id)
    )
    attr_key = result.scalar_one_or_none()

    if attr_key is None:
        return None

    attr_key.key = new_key
    await session.commit()
    await session.refresh(attr_key)
    return attr_key


async def delete_attribute_key(session: AsyncSession, key_id: int):
    result = await session.execute(
        select(AttributeKey).where(AttributeKey.id == key_id)
    )
    attr_key = result.scalar_one_or_none()

    if attr_key is None:
        raise HTTPException(
            status_code=404,
            detail=f"Attribute key {key_id} not found"
        )

    try:
        await session.delete(attr_key)
        await session.commit()
        return True

    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409,
                            detail=f"Cannot delete attribute key {key_id}: it is referenced by other objects")

    except SQLAlchemyError:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error while deleting attribute key {key_id}"
        )


async def fetch_all_attribute_values_with_keys(session: AsyncSession):
    query = select(AttributeValue).options(joinedload(AttributeValue.attr_key)).order_by(AttributeValue.id)
    result = await session.execute(query)
    values = result.scalars().all()

    return [
        {
            "id": v.id,
            "value": v.value,
            "alias": v.alias,
            "attr_key_id": v.attr_key_id,
            "key": v.attr_key.key,
        }
        for v in values
    ]


async def create_attribute(session: AsyncSession, payload: CreateAttribute) -> AttributeValue:
    key_exists_stmt = select(AttributeKey.id).where(AttributeKey.id == payload.key)
    key_exists = (await session.execute(key_exists_stmt)).scalar_one_or_none()
    if key_exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Attribute key {payload.key} not found", )

    stmt = (insert(AttributeValue).values(attr_key_id=payload.key, value=payload.attribute_name, alias=payload.alias)
            .returning(AttributeValue))

    try:
        result = await session.execute(stmt)
        new_value = result.scalar_one()
        await session.commit()
        return new_value

    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attribute value already exists for this key")


async def update_attribute_value(session: AsyncSession, value_id: int, new_value: str,
                                 new_alias: str | None) -> AttributeValue:
    exists_stmt = select(AttributeValue.id).where(AttributeValue.id == value_id)
    exists = (await session.execute(exists_stmt)).scalar_one_or_none()

    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Attribute not found")

    stmt = (update(AttributeValue).where(AttributeValue.id == value_id)
            .values(value=new_value, alias=new_alias).returning(AttributeValue))

    try:
        result = await session.execute(stmt)
        updated = result.scalar_one()
        await session.commit()
        return updated

    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attribute value already exists for this key")


async def delete_attribute_value(session: AsyncSession, value_id: int) -> bool | None:
    exists_stmt = select(AttributeValue.id).where(AttributeValue.id == value_id)
    exists = (await session.execute(exists_stmt)).scalar_one_or_none()

    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Attribute value not found")

    stmt = delete(AttributeValue).where(AttributeValue.id == value_id).returning(AttributeValue.id)

    try:
        result = await session.execute(stmt)
        deleted_id = result.scalar_one_or_none()

        if deleted_id is None:
            await session.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f"Failed to delete attribute")

        await session.commit()
        return True

    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Cannot delete attribute value {value_id}: it is referenced by other objects")


async def fetch_types_with_rules(session: AsyncSession):
    stmt = (
        select(ProductType)
        .options(
            selectinload(ProductType.attr_link).options(selectinload(AttributeLink.attr_key)),
            selectinload(ProductType.rule_overrides).options(selectinload(AttributeBrandRule.brand),
                                                             selectinload(AttributeBrandRule.attr_key)),
        )
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def fetch_all_brands(session: AsyncSession):
    result = await session.execute(select(ProductBrand))
    return result.scalars().all()


async def add_type_dependency_db(session: AsyncSession, type_id: int, attr_key_id: int):
    link = AttributeLink(product_type_id=type_id, attr_key_id=attr_key_id)
    session.add(link)
    await session.commit()
    await session.refresh(link)
    return link


async def delete_type_dependency_db(session: AsyncSession, type_id: int, attr_key_id: int):
    stmt = delete(AttributeLink).where(AttributeLink.product_type_id == type_id,
                                       AttributeLink.attr_key_id == attr_key_id)
    await session.execute(stmt)
    await session.commit()
    return {"type_id": type_id, "attr_key_id": attr_key_id}


async def add_attribute_brand_link_db(session: AsyncSession, data: AttributeBrandRuleLink):
    rule = AttributeBrandRule(product_type_id=data.product_type_id,
                              brand_id=data.brand_id,
                              attr_key_id=data.attr_key_id,
                              rule_type=data.rule_type)
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return AttributeBrandRuleLink(product_type_id=rule.product_type_id, brand_id=rule.brand_id,
                                  attr_key_id=rule.attr_key_id, rule_type=rule.rule_type)


async def delete_attribute_brand_link_db(session: AsyncSession, obj: AttributeBrandRuleLink):
    stmt = (delete(AttributeBrandRule).where(AttributeBrandRule.product_type_id == obj.product_type_id,
                                             AttributeBrandRule.brand_id == obj.brand_id,
                                             AttributeBrandRule.attr_key_id == obj.attr_key_id,
                                             AttributeBrandRule.rule_type == obj.rule_type))

    await session.execute(stmt)
    await session.commit()
    return obj


async def fetch_all_types(session: AsyncSession):
    result = await session.execute(select(ProductType))
    return result.scalars().all()


async def fetch_product_global(session: AsyncSession, product_type_id: int, brand_ids: list[int] | None = None):
    stmt = (
        select(ProductFeaturesGlobal)
        .options(selectinload(ProductFeaturesGlobal.brand))
        .where(ProductFeaturesGlobal.type_id == product_type_id)
        .order_by(ProductFeaturesGlobal.title.asc())
    )

    if brand_ids:
        stmt = stmt.where(ProductFeaturesGlobal.brand_id.in_(brand_ids))

    result = await session.execute(stmt)
    return result.scalars().all()


async def product_dependencies_keys_values(session: AsyncSession, payload: ProductDependenciesKeysValuesScheme):
    base_keys_stmt = (select(AttributeKey.id).join(AttributeLink, AttributeLink.attr_key_id == AttributeKey.id)
                      .where(AttributeLink.product_type_id == payload.product_type_id))

    base_key_ids = set((await session.scalars(base_keys_stmt)).all())
    rules_stmt = select(AttributeBrandRule.attr_key_id, AttributeBrandRule.rule_type).where(
        AttributeBrandRule.product_type_id == payload.product_type_id,
        AttributeBrandRule.brand_id == payload.brand_id)
    result = await session.execute(rules_stmt)
    rules = result.all()

    include_ids = {r[0] for r in rules if r[1] == OverrideType.include}
    exclude_ids = {r[0] for r in rules if r[1] == OverrideType.exclude}

    final_key_ids = (base_key_ids - exclude_ids) | include_ids

    if not final_key_ids:
        return []

    keys_stmt = select(AttributeKey).where(AttributeKey.id.in_(final_key_ids)).order_by(AttributeKey.key)
    keys = (await session.scalars(keys_stmt)).all()

    values_stmt = select(AttributeValue).where(AttributeValue.attr_key_id.in_(final_key_ids)).order_by(
        AttributeValue.value)
    values = (await session.scalars(values_stmt)).all()

    values_by_key = dict()
    for v in values:
        values_by_key.setdefault(v.attr_key_id, []).append(v)

    keys_list = list()

    for key in keys:
        values_list = list()

        values_for_key = values_by_key.get(key.id, [])
        for v in values_for_key:
            values_list.append(AttributeValueSchema(id=v.id, value=v.value, alias=v.alias))

        keys_list.append(AttributeKeySchema(
            key_id=key.id,
            key=key.key,
            values=values_list
        ))

    result = ProductDependenciesSchema(product_type_id=payload.product_type_id, brand_id=payload.brand_id,
                                       keys=keys_list)

    return result


async def add_product_attribute_value_option(payload: AttributeModelOptionLink, session: AsyncSession):
    for model_id in payload.model_ids:
        option = AttributeModelOption(model_id=model_id,
                                      attr_value_id=payload.attribute_value_id)
        session.add(option)
    try:
        await session.commit()
        return payload
    except IntegrityError:
        await session.rollback()


async def delete_product_attribute_value_option(payload: AttributeModelOptionLink, session: AsyncSession):
    stmt = delete(AttributeModelOption).where(AttributeModelOption.model_id.in_(payload.model_ids),
                                              AttributeModelOption.attr_value_id == payload.attribute_value_id)
    try:
        await session.execute(stmt)
        await session.commit()
        return payload
    except IntegrityError:
        await session.rollback()
