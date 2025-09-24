from aiogram_dialog import DialogManager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.crud_bot import get_menu_levels
from models import HUbMenuLevel


async def main_menu_getter(dialog_manager: DialogManager, session: AsyncSession, **kwargs):
    if "walk_history" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data["walk_history"] = [1]
        dialog_manager.dialog_data["parent_id"] = 1
    main = await get_menu_levels(session, 1)

    return {"main": main, 'last_path_level': False, 'back': False}


async def walking_dirs_getter(dialog_manager: DialogManager, session: AsyncSession, **kwargs):
    parent_id = dialog_manager.dialog_data["parent_id"]
    walk_history = dialog_manager.dialog_data.get("walk_history", [1])

    levels = await get_menu_levels(session, int(parent_id))
    query = select(HUbMenuLevel).where(HUbMenuLevel.id.in_(walk_history))
    execute = await session.execute(query)
    all_levels = execute.scalars().all()
    id_to_label = {level.id: level.label for level in all_levels}
    breadcrumb = "  >  ".join([id_to_label.get(i, f"[{i}]") for i in walk_history])

    return {"levels": levels, "breadcrumb": breadcrumb, "back": True}
