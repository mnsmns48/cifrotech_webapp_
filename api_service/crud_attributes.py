from fastapi import HTTPException
from sqlalchemy import select, update, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from starlette import status

from api_service.schemas import CreateAttribute, AttributeBrandRuleLink, ProductFeaturesAttributeOptions, \
    AttributeValueSchema, ModelAttributeValuesSchema, ModelAttributesRequest, ModelAttributesResponse, \
    AttributeModelOptionLink, AttributeOriginValueCheckRequest, AttributeOriginValueCheckResponse

from models import ProductType, AttributeKey, AttributeValue, AttributeLink, AttributeBrandRule, ProductBrand, \
    ProductFeaturesGlobal, AttributeModelOption
from models.attributes import OverrideType, AttributeOriginValue


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


async def load_model_attribute_options_db(session: AsyncSession,
                                          product_type_id: int) -> list[ProductFeaturesAttributeOptions]:
    stmt = (select(ProductFeaturesGlobal).where(ProductFeaturesGlobal.type_id == product_type_id)
            .order_by(ProductFeaturesGlobal.title)
            .options(selectinload(ProductFeaturesGlobal.brand), selectinload(ProductFeaturesGlobal.attribute_options)
                     .selectinload(AttributeModelOption.attr_value).selectinload(AttributeValue.attr_key)))

    result = await session.execute(stmt)
    models = result.scalars().all()

    response: list[ProductFeaturesAttributeOptions] = list()

    for model in models:
        grouped: dict[int, dict] = dict()

        for option in model.attribute_options:
            attr_value = option.attr_value
            attr_key = attr_value.attr_key

            if attr_key.id not in grouped:
                grouped[attr_key.id] = {"key_id": attr_key.id,
                                        "key": attr_key.key,
                                        "attr_value_ids": []}

            grouped[attr_key.id]["attr_value_ids"].append(
                AttributeValueSchema(id=attr_value.id, value=attr_value.value, alias=attr_value.alias)
            )

        response.append(
            ProductFeaturesAttributeOptions(model_id=model.id,
                                            title=model.title,
                                            brand_id=model.brand.id,
                                            brand=model.brand.brand,
                                            model_attribute_values=[ModelAttributeValuesSchema(**data)
                                                                    for data in grouped.values()],
                                            )
        )

    return response


async def product_dependencies_db(session: AsyncSession, payload: ModelAttributesRequest) -> ModelAttributesResponse:
    product_type_id = payload.product_type_id
    brand_id = payload.brand_id

    stmt_base = (
        select(AttributeKey.id, AttributeKey.key).join(AttributeLink, AttributeLink.attr_key_id == AttributeKey.id)
        .where(AttributeLink.product_type_id == product_type_id).order_by(AttributeKey.key)
    )
    base_rows = (await session.execute(stmt_base)).all()

    base_keys: dict[int, str] = {row.id: row.key for row in base_rows}

    stmt_rules = (
        select(AttributeBrandRule.attr_key_id, AttributeBrandRule.rule_type)
        .where(
            AttributeBrandRule.product_type_id == product_type_id,
            AttributeBrandRule.brand_id == brand_id,
        )
    )
    rule_rows = (await session.execute(stmt_rules)).all()

    include_keys: set[int] = set()
    exclude_keys: set[int] = set()

    for key_id, rule_type in rule_rows:
        if rule_type == OverrideType.include:
            include_keys.add(key_id)
        elif rule_type == OverrideType.exclude:
            exclude_keys.add(key_id)

    allowed_keys: set[int] = set(base_keys.keys())
    allowed_keys -= exclude_keys
    allowed_keys |= include_keys

    if not allowed_keys:
        return ModelAttributesResponse(
            product_type_id=product_type_id,
            brand_id=brand_id,
            titles=payload.titles,
            model_ids=payload.model_ids,
            model_attribute_values=[],
            model_attribute_values_exists=payload.model_attribute_values,
        )

    missing_key_ids = allowed_keys - set(base_keys.keys())
    if missing_key_ids:
        stmt_missing = (
            select(AttributeKey.id, AttributeKey.key)
            .where(AttributeKey.id.in_(missing_key_ids))
        )
        missing_rows = (await session.execute(stmt_missing)).all()
        for row in missing_rows:
            base_keys[row.id] = row.key

    stmt_values = (select(AttributeValue.id,
                          AttributeValue.value,
                          AttributeValue.alias,
                          AttributeValue.attr_key_id)
                   .where(AttributeValue.attr_key_id.in_(allowed_keys))
                   .order_by(AttributeValue.attr_key_id, AttributeValue.value))
    value_rows = (await session.execute(stmt_values)).all()

    grouped_values: dict[int, list[AttributeValueSchema]] = dict()
    for row in value_rows:
        key_id = row.attr_key_id
        grouped_values.setdefault(key_id, []).append(AttributeValueSchema(id=row.id, value=row.value, alias=row.alias))

    model_attribute_values: list[ModelAttributeValuesSchema] = list()

    for key_id in sorted(allowed_keys):
        model_attribute_values.append(
            ModelAttributeValuesSchema(key_id=key_id,
                                       key=base_keys.get(key_id, f"key_{key_id}"),
                                       attr_value_ids=grouped_values.get(key_id, [])))

    return ModelAttributesResponse(product_type_id=product_type_id, brand_id=brand_id,
                                   titles=payload.titles, model_ids=payload.model_ids,
                                   model_attribute_values=model_attribute_values,
                                   model_attribute_values_exists=payload.model_attribute_values)


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


async def attributes_origin_value_check_request_db(payload: AttributeOriginValueCheckRequest,
                                                   session: AsyncSession) -> AttributeOriginValueCheckResponse:
    BASE_SELECT = (
        select(AttributeValue.id, AttributeValue.value, AttributeValue.alias, AttributeKey.id.label("key_id"),
               AttributeKey.key.label("key_name"))
        .join(AttributeKey, AttributeKey.id == AttributeValue.attr_key_id))

    async def collect(stmt) -> dict[int, ModelAttributeValuesSchema]:
        result = await session.execute(stmt)
        collected: dict[int, ModelAttributeValuesSchema] = dict()

        for av_id, av_value, av_alias, key_id, key_name in result:
            if key_id not in collected:
                collected[key_id] = ModelAttributeValuesSchema(key_id=key_id, key=key_name, attr_value_ids=[])

            collected[key_id].attr_value_ids.append(
                AttributeValueSchema(id=av_id, value=av_value, alias=av_alias)
            )

        return collected

    stmt_allowable = (BASE_SELECT.join(AttributeModelOption, AttributeModelOption.attr_value_id == AttributeValue.id)
                      .where(AttributeModelOption.model_id == payload.model_id))
    allowable_map = await collect(stmt_allowable)

    stmt_exists = (BASE_SELECT.join(AttributeOriginValue, AttributeOriginValue.attr_value_id == AttributeValue.id)
                   .where(AttributeOriginValue.origin_id == payload.origin))
    exists_map = await collect(stmt_exists)

    return AttributeOriginValueCheckResponse(title=payload.title,
                                             attributes_allowable=list(allowable_map.values()),
                                             attributes_exists=list(exists_map.values()))
