from aiogram_dialog import DialogManager
from sqlalchemy.ext.asyncio import AsyncSession
from bot.crud_bot import get_menu_levels


async def menu_getter(dialog_manager: DialogManager, **kwargs):
    session: AsyncSession = dialog_manager.start_data["session"]
    parent_id: int = dialog_manager.start_data.get("parent_id", 1)
    levels = await get_menu_levels(session, parent_id)
    return {"levels": levels}
