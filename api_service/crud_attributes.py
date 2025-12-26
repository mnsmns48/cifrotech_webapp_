from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

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


async def delete_attribute_key(session: AsyncSession, key_id: int) -> bool:
    result = await session.execute(
        select(AttributeKey).where(AttributeKey.id == key_id)
    )
    attr_key = result.scalar_one_or_none()

    if attr_key is None:
        return False

    await session.delete(attr_key)
    await session.commit()
    return True


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
