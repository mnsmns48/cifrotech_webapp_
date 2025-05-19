from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.schemas import ParsingLogEvent

from models import User, Vendor, ParsingLog


async def add_parsing_event(parsing_event_data: ParsingLogEvent,
                            pg_session: AsyncSession):
    stmt_user = select(User.full_name).where(User.id == parsing_event_data.user)
    result_user = await pg_session.execute(stmt_user)
    full_name = result_user.scalar()
    stmt_vendor = select(Vendor.name).where(Vendor.id == int(parsing_event_data.vendor))
    result_vendor = await pg_session.execute(stmt_vendor)
    vendor_title = result_vendor.scalar()

    new_log = {'request_id': parsing_event_data.request_id,
               'user': full_name,
               'vendor_name': vendor_title,
               'parsing_title': parsing_event_data.parsing_title,
               'parsing_url': parsing_event_data.parsing_url,
               'result': parsing_event_data.result}

    await pg_session.execute(insert(ParsingLog).values(new_log))
    await pg_session.commit()
