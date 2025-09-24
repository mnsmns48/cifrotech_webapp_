from aiogram_dialog import DialogManager
from sqlalchemy.ext.asyncio import AsyncSession
from bot.crud_bot import get_menu_levels


async def menu_getter(dialog_manager: DialogManager, session: AsyncSession, **kwargs):
    parent_id = dialog_manager.dialog_data.get("parent_id", 1)
    levels = await get_menu_levels(session, parent_id)
    print(levels)
    return {"levels": levels}
