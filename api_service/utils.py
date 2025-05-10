from sqlalchemy.ext.asyncio import AsyncSession


async def update_instance_fields(instance, update_data: dict, session: AsyncSession):
    for key, value in update_data.items():
        setattr(instance, key, value)
    await session.commit()
    await session.refresh(instance)
