from fastapi import HTTPException
from sqlalchemy import select, update, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from starlette import status

from api_service.schemas.attribute_schemas import CreateAttribute
from models.attributes import AttributeKey, AttributeValue


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
